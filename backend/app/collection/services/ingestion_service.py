from datetime import datetime, timezone

from app.core.extensions import db
from app.collection.sources.base import ProviderError
from app.collection.sources.ncpssd import NcpssdSource
from app.collection.sources.elsevier import ElsevierSource
from app.collection.repositories.raw_issue_repo import RawIssueRepository
from app.collection.repositories.raw_paper_repo import RawPaperRepository
from app.collection.services.artifact_service import ArtifactService
from app.collection.services.task_service import TaskService


class IngestionService:
    def __init__(
        self,
        raw_issue_repo=None,
        raw_paper_repo=None,
        task_service=None,
        artifact_service=None,
        providers=None,
    ):
        self.raw_issue_repo = raw_issue_repo or RawIssueRepository()
        self.raw_paper_repo = raw_paper_repo or RawPaperRepository()
        self.task_service = task_service or TaskService()
        self.artifact_service = artifact_service or ArtifactService()
        self.providers = providers or {
            "domestic": NcpssdSource(),
            "foreign": ElsevierSource(),
        }

    def run_ingestion(self, source_type, journal_name, year, issue):
        provider = self.providers.get(source_type)
        if provider is None:
            raise ValueError(f"Unsupported source type: {source_type}")

        task = self.task_service.create_task(
            task_type="crawl",
            source_type=source_type,
            journal_name=journal_name,
            year=year,
            issue=str(issue),
            status="running",
            progress_message="Starting crawl",
            started_at=datetime.now(timezone.utc),
        )
        self.task_service.append_log(task, "Task created")
        try:
            payload = provider.fetch_issue(journal_name, year, issue)
            raw_issue = self.save_issue_payload(
                task=task,
                issue_data=payload["issue"],
                papers=payload["papers"],
            )
            self.artifact_service.export_raw_issue(raw_issue)

            task = self.task_service.update_task(
                task.id,
                status="completed",
                progress_message="Crawl completed",
                error_message=None,
                finished_at=datetime.now(timezone.utc),
            )
            self.task_service.append_log(task, "Issue payload persisted")
            db.session.refresh(raw_issue)
            db.session.refresh(task)
            return task, raw_issue
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

    def save_issue_payload(self, task, issue_data, papers):
        raw_issue = self.raw_issue_repo.get_by_identity(
            source_type=issue_data["source_type"],
            journal_name=issue_data["journal_name"],
            year=issue_data["year"],
            issue=issue_data["issue"],
        )

        raw_issue_data = {
            "source_type": issue_data["source_type"],
            "journal_name": issue_data["journal_name"],
            "journal_slug": issue_data.get("journal_slug"),
            "year": issue_data["year"],
            "issue": issue_data["issue"],
            "volume": issue_data.get("volume"),
            "language": issue_data.get("language", "mixed"),
            "source_url": issue_data.get("source_url"),
            "paper_count": len(papers),
            "crawl_task_id": task.id,
        }

        if raw_issue is None:
            raw_issue = self.raw_issue_repo.create(**raw_issue_data)
        else:
            raw_issue = self.raw_issue_repo.update(raw_issue.id, **raw_issue_data)

        self.raw_paper_repo.replace_for_issue(raw_issue, papers)
        db.session.refresh(raw_issue)
        return raw_issue
