import hashlib
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app

from app.collection.models import (
    FullTextTask,
    FullTextTaskItem,
    LiteratureSource,
    RawIssue,
)
from app.collection.fulltext.base import FullTextProviderError, NotPdfError, TooLargeError
from app.collection.fulltext.registry import (
    build_fulltext_provider,
    resolve_fulltext_reference,
)
from app.core.extensions import db
from app.papers.models import Literature


_ACTIVE_STATUSES = ("pending", "running", "waiting_user")


class FullTextError(ValueError):
    pass


class FullTextConflictError(FullTextError):
    pass


def source_reference(raw_paper):
    reference = resolve_fulltext_reference(raw_paper)
    return reference.paper_ref if reference else None


class FullTextService:
    def __init__(self, source_factory=None, max_pdf_size=100 * 1024 * 1024):
        self.source_factory = source_factory or self._build_source
        self.max_pdf_size = int(max_pdf_size)

    @staticmethod
    def _build_source(source_type, journal_name):
        return build_fulltext_provider(source_type, journal_name)

    @staticmethod
    def _resolve_literature(literature, preferred_provider=None):
        candidates = []
        for link in literature.collection_sources:
            if link.raw_paper is None:
                continue
            reference = resolve_fulltext_reference(link.raw_paper)
            if reference is None:
                continue
            candidates.append((link, reference))
        if preferred_provider:
            candidates = [
                candidate
                for candidate in candidates
                if candidate[1].provider_id == preferred_provider
            ]
        priorities = {"magtech": 200, "sciencedirect": 100}
        return max(
            candidates,
            key=lambda candidate: (
                priorities.get(candidate[1].provider_id, 0),
                candidate[0].raw_paper_id,
            ),
            default=None,
        )

    def create_single_task(self, literature_id, replace_existing=False):
        literature = db.session.get(Literature, literature_id)
        if literature is None:
            raise FullTextError("文献不存在")

        active = (
            FullTextTaskItem.query.join(FullTextTask)
            .filter(
                FullTextTaskItem.literature_id == literature.id,
                FullTextTask.status.in_(_ACTIVE_STATUSES),
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
            if not replace_existing:
                raise FullTextConflictError("文献已有 PDF，请明确选择重新获取")

        preferred_provider = literature.pdf_source_type if literature.pdf_path else None
        resolved = self._resolve_literature(literature, preferred_provider=preferred_provider)
        if resolved is None:
            if preferred_provider:
                raise FullTextConflictError("当前 PDF 来源已无法匹配，不能自动替换")
            raise FullTextError("该文献没有可用的全文来源")
        link, reference = resolved

        task = FullTextTask(
            mode="single",
            source_type=reference.provider_id,
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
                source_type=reference.provider_id,
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

        active = (
            FullTextTask.query.filter(
                FullTextTask.raw_issue_id == raw_issue.id,
                FullTextTask.mode.in_(("issue", "after_ingestion")),
                FullTextTask.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(FullTextTask.id.desc())
            .first()
        )
        if active is not None:
            active._was_created = False
            return active

        prepared = []
        provider_ids = set()
        for raw_paper in raw_issue.papers:
            link = raw_paper.literature_sources[0] if raw_paper.literature_sources else None
            literature = link.literature if link else None
            reference = resolve_fulltext_reference(raw_paper)
            if reference is not None:
                provider_ids.add(reference.provider_id)
            prepared.append((raw_paper, literature, reference))
        if not provider_ids:
            raise FullTextError("该期号没有可用的全文来源")

        task = FullTextTask(
            mode=mode,
            source_type=next(iter(provider_ids)) if len(provider_ids) == 1 else "mixed",
            raw_issue_id=raw_issue.id,
            status="pending",
            replace_existing=False,
            total_count=len(raw_issue.papers),
            progress_message="等待下载",
        )
        db.session.add(task)
        db.session.flush()
        for raw_paper, literature, reference in prepared:
            active_item = None
            if literature is not None:
                active_item = (
                    FullTextTaskItem.query.join(FullTextTask)
                    .filter(
                        FullTextTaskItem.literature_id == literature.id,
                        FullTextTask.status.in_(_ACTIVE_STATUSES),
                    )
                    .first()
                )
            status = "pending"
            failure_code = None
            message = None
            if literature is None:
                status = "failed"
                failure_code = "not_linked"
                message = "原始论文未关联到统一文献"
            elif literature.pdf_path:
                status = "skipped"
                message = "已有 PDF，已跳过"
            elif active_item is not None:
                status = "skipped"
                message = "已有全文任务正在处理，已跳过"
            elif reference is None:
                status = "failed"
                failure_code = "not_supported"
                message = "该论文没有可用的全文来源"
            db.session.add(
                FullTextTaskItem(
                    task_id=task.id,
                    literature_id=literature.id if literature else None,
                    raw_paper_id=raw_paper.id,
                    source_type=reference.provider_id if reference else "unresolved",
                    status=status,
                    failure_code=failure_code,
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
            raise NotPdfError("下载结果不是有效的 PDF 文件")
        if len(content) > self.max_pdf_size:
            raise TooLargeError("PDF 文件超过 100 MB 上限")

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
        literature.pdf_source_type = item.source_type
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
        task.finished_at = None
        task.error_message = None
        task.progress_message = "正在下载全文"
        db.session.commit()

        sources = {}
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
                    if literature.pdf_source_type != item.source_type or not task.replace_existing:
                        item.status = "skipped"
                        item.error_message = "已有 PDF，已跳过"
                        item.finished_at = datetime.now(UTC)
                        self._refresh_counts(task)
                        db.session.commit()
                        continue
                reference = resolve_fulltext_reference(raw_paper)
                if reference is None:
                    raise FullTextError("该论文没有可用的全文来源")
                if reference.provider_id != item.source_type:
                    raise FullTextError("全文来源与任务快照不一致")
                source = sources.get(item.source_type)
                if source is None:
                    source = self.source_factory(
                        item.source_type,
                        raw_paper.raw_issue.journal_name,
                    )
                    sources[item.source_type] = source
                result = source.download_pdf(
                    reference.paper_ref,
                    download_dir=Path(current_app.config["UPLOAD_FOLDER"]),
                    max_pdf_size=self.max_pdf_size,
                )
                self._save_pdf(task, item, literature, raw_paper, result)
                item.status = "completed"
                item.failure_code = None
                item.action_url = None
                item.error_message = None
            except FullTextProviderError as exc:
                if exc.requires_user_action:
                    item.status = "waiting_user"
                    item.failure_code = exc.code
                    item.action_url = exc.action_url
                    item.error_message = str(exc)
                    item.finished_at = None
                    task.status = "waiting_user"
                    task.progress_message = str(exc)
                    self._refresh_counts(task)
                    db.session.commit()
                    return task
                item.status = "failed"
                item.failure_code = exc.code
                item.action_url = exc.action_url
                item.error_message = str(exc)
            except Exception as exc:
                item.status = "failed"
                item.failure_code = "not_pdf" if isinstance(exc, FullTextError) else "remote_error"
                item.error_message = str(exc)
            finally:
                if item.status != "waiting_user":
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

    def resume_task(self, task_id):
        task = db.session.get(FullTextTask, task_id)
        if task is None:
            raise FullTextError("全文任务不存在")
        if task.status != "waiting_user":
            raise FullTextConflictError("只有等待用户处理的全文任务可以继续")
        waiting_items = [item for item in task.items if item.status == "waiting_user"]
        if not waiting_items:
            raise FullTextConflictError("任务没有等待处理的论文")
        for item in waiting_items:
            item.status = "pending"
            item.failure_code = None
            item.action_url = None
            item.error_message = None
            item.started_at = None
            item.finished_at = None
        task.status = "pending"
        task.progress_message = "等待继续下载"
        task.error_message = None
        task.finished_at = None
        db.session.commit()
        return task

    def mark_failed(self, task_id, exc):
        task = db.session.get(FullTextTask, task_id)
        if task is None or task.status in ("completed", "partial", "failed", "waiting_user"):
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
