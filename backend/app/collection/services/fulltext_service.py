import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app

from app.collection.models import (
    FullTextTask,
    FullTextTaskItem,
    LiteratureSource,
    RawIssue,
)
from app.collection.sources.registry import get_source
from app.core.extensions import db
from app.papers.models import Literature


_ARTICLE_ID_RE = re.compile(r"(?:article_|abstract)(\d+)\.shtml", re.IGNORECASE)
_RUNNING_STATUSES = ("pending", "running")


class FullTextError(ValueError):
    pass


class FullTextConflictError(FullTextError):
    pass


def source_reference(raw_paper):
    try:
        parsed = json.loads(raw_paper.source_ref_json or "{}")
    except (TypeError, ValueError):
        parsed = {}
    if isinstance(parsed, dict) and parsed.get("article_id"):
        return {"article_id": str(parsed["article_id"])}
    match = _ARTICLE_ID_RE.search(raw_paper.detail_url or "")
    return {"article_id": match.group(1)} if match else None


class FullTextService:
    def __init__(self, source_factory=None, max_pdf_size=100 * 1024 * 1024):
        self.source_factory = source_factory or self._build_source
        self.max_pdf_size = int(max_pdf_size)

    @staticmethod
    def _build_source(source_type, journal_name):
        from app.collection.services.ingestion_service import load_source_config

        return get_source(source_type, load_source_config(journal_name, source_type))

    @staticmethod
    def _magtech_link(literature):
        links = [
            link
            for link in literature.collection_sources
            if link.source_type == "magtech" and link.raw_paper is not None
        ]
        return max(links, key=lambda link: link.raw_paper_id, default=None)

    def create_single_task(self, literature_id, replace_existing=False):
        literature = db.session.get(Literature, literature_id)
        if literature is None:
            raise FullTextError("文献不存在")

        active = (
            FullTextTaskItem.query.join(FullTextTask)
            .filter(
                FullTextTaskItem.literature_id == literature.id,
                FullTextTask.status.in_(_RUNNING_STATUSES),
            )
            .order_by(FullTextTask.id.desc())
            .first()
        )
        if active is not None:
            active.task._was_created = False
            return active.task

        if literature.pdf_path:
            if literature.pdf_source_type in (None, "user"):
                raise FullTextConflictError("用户上传的 PDF 不允许被自动采集覆盖")
            if literature.pdf_source_type != "magtech":
                raise FullTextConflictError("只能重新获取并替换 Magtech 官网采集的 PDF")
            if not replace_existing:
                raise FullTextConflictError("文献已有 PDF，请明确选择重新获取")

        link = self._magtech_link(literature)
        if link is None:
            raise FullTextError("该文献没有可用于全文采集的 Magtech 官网来源")

        task = FullTextTask(
            mode="single",
            source_type="magtech",
            raw_issue_id=link.raw_paper.raw_issue_id,
            status="pending",
            replace_existing=bool(replace_existing),
            total_count=1,
            progress_message="等待下载",
        )
        db.session.add(task)
        db.session.flush()
        db.session.add(
            FullTextTaskItem(
                task_id=task.id,
                literature_id=literature.id,
                raw_paper_id=link.raw_paper_id,
                source_type="magtech",
                status="pending",
            )
        )
        db.session.commit()
        task._was_created = True
        return task

    def create_issue_task(self, raw_issue_id, mode="issue"):
        raw_issue = db.session.get(RawIssue, raw_issue_id)
        if raw_issue is None:
            raise FullTextError("采集期号不存在")
        if raw_issue.source_type != "magtech":
            raise FullTextError("当前仅支持从 Magtech 期刊官网下载全文")

        active = (
            FullTextTask.query.filter(
                FullTextTask.raw_issue_id == raw_issue.id,
                FullTextTask.mode.in_(("issue", "after_ingestion")),
                FullTextTask.status.in_(_RUNNING_STATUSES),
            )
            .order_by(FullTextTask.id.desc())
            .first()
        )
        if active is not None:
            active._was_created = False
            return active

        task = FullTextTask(
            mode=mode,
            source_type="magtech",
            raw_issue_id=raw_issue.id,
            status="pending",
            replace_existing=False,
            total_count=len(raw_issue.papers),
            progress_message="等待下载",
        )
        db.session.add(task)
        db.session.flush()
        for raw_paper in raw_issue.papers:
            link = raw_paper.literature_sources[0] if raw_paper.literature_sources else None
            literature = link.literature if link else None
            active_item = None
            if literature is not None:
                active_item = (
                    FullTextTaskItem.query.join(FullTextTask)
                    .filter(
                        FullTextTaskItem.literature_id == literature.id,
                        FullTextTask.status.in_(_RUNNING_STATUSES),
                    )
                    .first()
                )
            status = (
                "skipped"
                if literature is not None and (literature.pdf_path or active_item is not None)
                else "pending"
            )
            message = None
            if literature is not None and literature.pdf_path:
                message = "已有 PDF，已跳过"
            elif active_item is not None:
                message = "已有全文任务正在处理，已跳过"
            db.session.add(
                FullTextTaskItem(
                    task_id=task.id,
                    literature_id=literature.id if literature else None,
                    raw_paper_id=raw_paper.id,
                    source_type="magtech",
                    status=status,
                    error_message=message,
                )
            )
        self._refresh_counts(task)
        db.session.commit()
        task._was_created = True
        return task

    @staticmethod
    def _refresh_counts(task):
        task.total_count = len(task.items)
        task.succeeded_count = sum(item.status == "completed" for item in task.items)
        task.failed_count = sum(item.status == "failed" for item in task.items)
        task.skipped_count = sum(item.status == "skipped" for item in task.items)

    def _validate_download(self, content):
        if not content or not content.startswith(b"%PDF-"):
            raise FullTextError("下载结果不是有效的 PDF 文件")
        if len(content) > self.max_pdf_size:
            raise FullTextError("PDF 文件超过 100 MB 上限")

    def _save_pdf(self, task, item, literature, raw_paper, result):
        self._validate_download(result.content)
        upload_root = Path(current_app.config["UPLOAD_FOLDER"])
        upload_root.mkdir(parents=True, exist_ok=True)
        target = upload_root / f"{literature.id}.pdf"
        temporary = target.with_name(f"{target.name}.part-{task.id}-{item.id}")
        try:
            temporary.write_bytes(result.content)
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()

        digest = hashlib.sha256(result.content).hexdigest()
        relative_path = f"uploads/pdfs/{literature.id}.pdf"
        literature.pdf_path = relative_path
        literature.pdf_source_type = "magtech"
        literature.pdf_source_raw_paper_id = raw_paper.id
        literature.pdf_sha256 = digest
        literature.pdf_size_bytes = len(result.content)
        item.source_url = result.source_url
        item.pdf_path = relative_path
        item.file_size_bytes = len(result.content)
        item.sha256 = digest

    def run_task(self, task_id):
        task = db.session.get(FullTextTask, task_id)
        if task is None:
            raise FullTextError("全文任务不存在")
        task.status = "running"
        task.started_at = datetime.now(UTC)
        task.progress_message = "正在下载全文"
        db.session.commit()

        for item in task.items:
            if item.status != "pending":
                continue
            item.status = "running"
            item.started_at = datetime.now(UTC)
            db.session.commit()
            try:
                literature = db.session.get(Literature, item.literature_id)
                raw_paper = item.raw_paper
                if literature is None or raw_paper is None:
                    raise FullTextError("原始论文未关联到统一文献")
                if literature.pdf_path:
                    if literature.pdf_source_type != "magtech" or not task.replace_existing:
                        item.status = "skipped"
                        item.error_message = "已有 PDF，已跳过"
                        continue
                reference = source_reference(raw_paper)
                if reference is None:
                    raise FullTextError("缺少 Magtech 文章标识，无法下载全文")
                source = self.source_factory("magtech", raw_paper.raw_issue.journal_name)
                result = source.download_pdf(reference)
                self._save_pdf(task, item, literature, raw_paper, result)
                item.status = "completed"
                item.error_message = None
            except Exception as exc:
                item.status = "failed"
                item.error_message = str(exc)
            finally:
                item.finished_at = datetime.now(UTC)
                self._refresh_counts(task)
                task.progress_message = (
                    f"已处理 {task.succeeded_count + task.failed_count + task.skipped_count}"
                    f"/{task.total_count} 篇"
                )
                db.session.commit()

        self._refresh_counts(task)
        if task.failed_count:
            task.status = "partial" if task.succeeded_count or task.skipped_count else "failed"
            task.error_message = f"{task.failed_count} 篇全文获取失败"
        else:
            task.status = "completed"
            task.error_message = None
        task.finished_at = datetime.now(UTC)
        task.progress_message = (
            f"成功 {task.succeeded_count} 篇，失败 {task.failed_count} 篇，"
            f"跳过 {task.skipped_count} 篇"
        )
        db.session.commit()
        return task

    def mark_failed(self, task_id, exc):
        task = db.session.get(FullTextTask, task_id)
        if task is None or task.status in ("completed", "partial", "failed"):
            return
        task.status = "failed"
        task.error_message = str(exc)
        task.finished_at = datetime.now(UTC)
        db.session.commit()

    def list_tasks(self, literature_id=None, raw_issue_id=None, limit=20):
        query = FullTextTask.query
        if literature_id is not None:
            query = query.join(FullTextTaskItem).filter(
                FullTextTaskItem.literature_id == literature_id
            )
        if raw_issue_id is not None:
            query = query.filter(FullTextTask.raw_issue_id == raw_issue_id)
        return query.order_by(FullTextTask.id.desc()).limit(limit).all()
