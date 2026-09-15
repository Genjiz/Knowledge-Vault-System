from app.collection.models import RawIssue, RawIssueAnalysis
from app.collection.providers.analysis_provider import AnalysisProvider
from app.collection.services.artifact_service import ArtifactService
from app.core.extensions import db
from app.core.llm.service import require_enabled_profile


class AnalysisService:
    def __init__(self, provider=None, artifact_service=None):
        self.provider = provider or AnalysisProvider()
        self.artifact_service = artifact_service or ArtifactService()

    def analyze_issue(self, raw_issue_id, profile_id):
        raw_issue = db.session.get(RawIssue, raw_issue_id)
        if raw_issue is None:
            raise ValueError(f"Raw issue not found: {raw_issue_id}")
        profile = require_enabled_profile(profile_id)
        markdown = self.provider.generate_analysis(
            raw_issue, raw_issue.papers, profile_id=profile.id
        )

        analysis = RawIssueAnalysis.query.filter_by(raw_issue_id=raw_issue.id).first()
        if analysis is None:
            analysis = RawIssueAnalysis(raw_issue_id=raw_issue.id)
            db.session.add(analysis)

        analysis.model_name = getattr(self.provider, "model_name", None) or profile.model_name
        analysis.prompt_version = "journal_analysis"
        analysis.content_markdown = markdown
        analysis.status = "completed"
        analysis.error_message = None
        raw_issue.analysis_status = "completed"

        db.session.commit()
        self.artifact_service.export_analysis(analysis)
        db.session.refresh(analysis)
        db.session.refresh(raw_issue)
        return analysis
