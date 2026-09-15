import json
from collections import OrderedDict
from datetime import datetime, timezone

from app.core.extensions import db
from app.collection.sources.base import ProviderError
from app.collection.sources.registry import get_source
from app.collection.repositories.raw_issue_repo import RawIssueRepository
from app.collection.repositories.raw_paper_repo import RawPaperRepository
from app.collection.services.artifact_service import ArtifactService
from app.collection.services.task_service import TaskService
from app.collection.pipeline.paper_merge import PaperMergeService


UNKNOWN_VOLUME = "unknown"
UNASSIGNED_ISSUE = "unassigned"


def load_source_config(journal_name, source_id):
    """读取期刊在某采集源下的配置（如 Magtech 的 base_url）。

    期刊-源配置由 papers 域的 journal_source_config 承载；未配置或未启用时
    返回空 dict，由源自身决定缺少必填配置时如何报错。
    """
    from app.papers.models import Journal, JournalSourceConfig

    row = (
        JournalSourceConfig.query.join(Journal, Journal.id == JournalSourceConfig.journal_id)
        .filter(
            Journal.name == journal_name,
            JournalSourceConfig.source_id == source_id,
            JournalSourceConfig.enabled.is_(True),
        )
        .first()
    )
    if row is None or not row.config_json:
        return {}
    try:
        return json.loads(row.config_json)
    except (TypeError, ValueError):
        return {}


def load_journal_issn(journal_name):
    from app.papers.models import Journal

    journal = Journal.query.filter(Journal.name == journal_name).first()
    return journal.issn if journal is not None else None


class IngestionService:
    def __init__(
        self,
        raw_issue_repo=None,
        raw_paper_repo=None,
        task_service=None,
        artifact_service=None,
        providers=None,
        paper_merge=None,
        config_loader=None,
    ):
        self.raw_issue_repo = raw_issue_repo or RawIssueRepository()
        self.raw_paper_repo = raw_paper_repo or RawPaperRepository()
        self.task_service = task_service or TaskService()
        self.paper_merge = paper_merge or PaperMergeService()
        self.artifact_service = artifact_service or ArtifactService()
        # providers 仅测试注入用（source_id → 实例）；生产路径统一走注册表
        self.providers = providers
        self.config_loader = config_loader or load_source_config

    def _resolve_provider(self, source_id, journal_name):
        if self.providers is not None:
            return self.providers.get(source_id)
        return get_source(source_id, self.config_loader(journal_name, source_id))

    def run_ingestion(
        self,
        source_type,
        journal_name,
        year,
        issue,
        *,
        target_volume=None,
        target_issue=None,
    ):
        # source_type 即真实采集源 id（ncpssd/magtech/elsevier/scopus）
        provider = self._resolve_provider(source_type, journal_name)
        if provider is None:
            raise ValueError(f"Unsupported source type: {source_type}")
        ingest_scope = getattr(provider, "ingest_scope", "issue")
        normalized_issue = "year" if ingest_scope == "year" else str(issue)

        task = self.task_service.create_task(
            task_type="crawl",
            source_type=source_type,
            region=getattr(provider, "region", None),
            journal_name=journal_name,
            year=year,
            issue=normalized_issue,
            status="running",
            progress_message="Starting crawl",
            started_at=datetime.now(timezone.utc),
        )
        self.task_service.append_log(task, "Task created")
        try:
            fetch_kwargs = {}
            if ingest_scope == "year":
                fetch_kwargs["issn"] = load_journal_issn(journal_name)
            payload = provider.fetch_issue(
                journal_name, year, normalized_issue, **fetch_kwargs
            )
            scoped_payloads = self._split_payload(
                payload,
                ingest_scope,
                target_volume=target_volume,
                target_issue=target_issue,
            )
            raw_issues = []
            for scoped_payload in scoped_payloads:
                raw_issue = self.save_issue_payload(
                    task=task,
                    issue_data=scoped_payload["issue"],
                    papers=scoped_payload["papers"],
                )
                self.artifact_service.export_raw_issue(raw_issue)
                self.paper_merge.sync_issue(
                    raw_issue,
                    affected_literature_ids=getattr(raw_issue, "_affected_literature_ids", None),
                )
                raw_issues.append(raw_issue)

            task = self.task_service.update_task(
                task.id,
                status="completed",
                progress_message="Crawl completed",
                error_message=None,
                finished_at=datetime.now(timezone.utc),
            )
            self.task_service.append_log(task, "Issue payload persisted")
            dropped = int(payload["issue"].get("dropped_paper_count") or 0)
            if dropped:
                self.task_service.append_log(
                    task,
                    f"丢弃 {dropped} 条无效或重复的 Scopus 记录",
                    level="warning",
                )
            actual_count = sum(item.paper_count for item in raw_issues)
            try:
                expected_count = int(payload["issue"].get("paper_count_hint"))
            except (TypeError, ValueError):
                expected_count = actual_count
            if expected_count != actual_count:
                self.task_service.append_log(
                    task,
                    "实际入库数与 Scopus 返回总数不一致："
                    f"expected={expected_count}, actual={actual_count}",
                    level="warning",
                )
            for raw_issue in raw_issues:
                db.session.refresh(raw_issue)
            db.session.refresh(task)
            return task, raw_issues
        except Exception as exc:
            task = self.task_service.update_task(
                task.id,
                status="failed",
                progress_message="Crawl failed",
                error_message=str(exc),
                finished_at=datetime.now(timezone.utc),
            )
            self.task_service.append_log(task, f"Crawl failed: {exc}", level="error")
            raise ProviderError(str(exc)) from exc

    @staticmethod
    def _split_payload(payload, ingest_scope, *, target_volume=None, target_issue=None):
        """年度来源按真实卷期拆分；按期来源保持原合同。"""
        if ingest_scope != "year":
            return [payload]

        groups = OrderedDict()
        for paper in payload.get("papers") or []:
            volume = str(paper.get("volume") or "").strip() or UNKNOWN_VOLUME
            issue = str(paper.get("issue") or "").strip() or UNASSIGNED_ISSUE
            groups.setdefault((volume, issue), []).append(paper)

        scoped = []
        for (volume, issue), papers in groups.items():
            if target_issue is not None:
                normalized_target_volume = (
                    str(target_volume or "").strip() or UNKNOWN_VOLUME
                )
                normalized_target_issue = (
                    str(target_issue or "").strip() or UNASSIGNED_ISSUE
                )
                if (volume, issue) != (
                    normalized_target_volume,
                    normalized_target_issue,
                ):
                    continue
            issue_data = dict(payload["issue"])
            issue_data.update(
                {
                    "volume": volume,
                    "issue": issue,
                    "paper_count_hint": len(papers),
                }
            )
            scoped.append({"issue": issue_data, "papers": papers})
        if target_issue is not None and not scoped:
            raise ProviderError(
                f"Scopus 本次年度结果中未找到 Vol.{target_volume or '未知'} "
                f"第 {target_issue or '未分期'} 期，原批次未被覆盖"
            )
        return scoped

    def save_issue_payload(self, task, issue_data, papers):
        raw_issue = self.raw_issue_repo.get_by_identity(
            source_type=issue_data["source_type"],
            journal_name=issue_data["journal_name"],
            year=issue_data["year"],
            volume=str(issue_data.get("volume") or "").strip() or UNKNOWN_VOLUME,
            issue=issue_data["issue"],
        )

        try:
            expected_paper_count = int(issue_data.get("paper_count_hint"))
            if expected_paper_count < 0:
                raise ValueError
        except (TypeError, ValueError):
            expected_paper_count = len(papers)

        raw_issue_data = {
            "source_type": issue_data["source_type"],
            "region": issue_data.get("region") or getattr(task, "region", None),
            "journal_name": issue_data["journal_name"],
            "journal_slug": issue_data.get("journal_slug"),
            "year": issue_data["year"],
            "issue": issue_data["issue"],
            "volume": str(issue_data.get("volume") or "").strip() or UNKNOWN_VOLUME,
            "language": issue_data.get("language", "mixed"),
            "source_url": issue_data.get("source_url"),
            "expected_paper_count": expected_paper_count,
            "paper_count": len(papers),
            "crawl_task_id": task.id,
        }

        affected_literature_ids = set()
        if raw_issue is None:
            raw_issue = self.raw_issue_repo.create(**raw_issue_data)
        else:
            affected_literature_ids = self.paper_merge.unlink_issue(raw_issue)
            raw_issue = self.raw_issue_repo.update(raw_issue.id, **raw_issue_data)

        self.raw_paper_repo.replace_for_issue(raw_issue, papers)
        db.session.refresh(raw_issue)
        raw_issue._affected_literature_ids = affected_literature_ids
        return raw_issue
