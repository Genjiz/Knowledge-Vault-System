from app.collection.models import FullTextTask, FullTextTaskItem, LLMRun, LiteratureSource, RawIssue
from app.collection.pipeline.paper_merge import PaperMergeService
from app.collection.services.artifact_service import ArtifactService
from app.core.extensions import db
from app.papers.models import Literature


class RawIssueService:
    def __init__(self, paper_merge=None, artifact_service=None):
        self.paper_merge = paper_merge or PaperMergeService()
        self.artifact_service = artifact_service or ArtifactService()

    def delete_issue(self, raw_issue_id):
        raw_issue = db.session.get(RawIssue, raw_issue_id)
        if raw_issue is None:
            return None

        raw_paper_ids = [paper.id for paper in raw_issue.papers]
        analysis_ids = [analysis.id for analysis in raw_issue.analyses]
        artifact_paths = [raw_issue.raw_json_path]
        artifact_paths.extend(analysis.artifact_md_path for analysis in raw_issue.analyses)

        links = []
        if raw_paper_ids:
            links = LiteratureSource.query.filter(
                LiteratureSource.raw_paper_id.in_(raw_paper_ids)
            ).all()
        affected_literature_ids = {link.literature_id for link in links}

        if raw_paper_ids:
            LLMRun.query.filter(LLMRun.raw_paper_id.in_(raw_paper_ids)).delete(
                synchronize_session=False
            )
        if analysis_ids:
            LLMRun.query.filter(LLMRun.raw_issue_analysis_id.in_(analysis_ids)).delete(
                synchronize_session=False
            )
        if raw_paper_ids:
            FullTextTaskItem.query.filter(
                FullTextTaskItem.raw_paper_id.in_(raw_paper_ids)
            ).update({FullTextTaskItem.raw_paper_id: None}, synchronize_session=False)
            Literature.query.filter(
                Literature.pdf_source_raw_paper_id.in_(raw_paper_ids)
            ).update({Literature.pdf_source_raw_paper_id: None}, synchronize_session=False)
        FullTextTask.query.filter_by(raw_issue_id=raw_issue.id).update(
            {FullTextTask.raw_issue_id: None}, synchronize_session=False
        )

        db.session.delete(raw_issue)
        db.session.flush()

        for literature_id in affected_literature_ids:
            literature = db.session.get(Literature, literature_id)
            if literature is not None:
                self.paper_merge.recompute_literature(literature, commit=False)
        db.session.commit()

        deleted_files = self.artifact_service.delete_files(artifact_paths)
        return {
            "id": raw_issue_id,
            "affected_literature_count": len(affected_literature_ids),
            "deleted_artifact_count": len(deleted_files),
        }
