from app.collection.models import RawIssue
from app.collection.services.artifact_service import ArtifactService
from app.core.extensions import db


class TranslationService:
    def __init__(self, provider, artifact_service=None):
        self.provider = provider
        self.artifact_service = artifact_service or ArtifactService()

    def translate_issue(self, raw_issue_id):
        raw_issue = db.session.get(RawIssue, raw_issue_id)
        if raw_issue is None:
            raise ValueError(f"Raw issue not found: {raw_issue_id}")
        translations = self.provider.translate_papers(raw_issue.papers)

        for paper, translated in zip(raw_issue.papers, translations):
            paper.title_zh = translated.get("title_zh", "")
            paper.abstract_zh = translated.get("abstract_zh", "")
            paper.translation_status = "completed"

        raw_issue.translation_status = "completed"
        db.session.commit()
        self.artifact_service.export_raw_issue(raw_issue)
        db.session.refresh(raw_issue)
        return raw_issue
