from app.extensions import db
from app.models.base import BaseModel


class RawIssueAnalysis(BaseModel):
    __tablename__ = "raw_issue_analysis"

    raw_issue_id = db.Column(db.Integer, db.ForeignKey("raw_issue.id"), nullable=False, index=True)
    model_name = db.Column(db.String(100))
    prompt_version = db.Column(db.String(50))
    content_markdown = db.Column(db.Text)
    artifact_md_path = db.Column(db.String(500))
    status = db.Column(db.String(32), nullable=False, default="pending")
    error_message = db.Column(db.Text)

    raw_issue = db.relationship("RawIssue", back_populates="analyses")
    llm_runs = db.relationship("LLMRun", back_populates="raw_issue_analysis", lazy="selectin")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "raw_issue_id": self.raw_issue_id,
                "model_name": self.model_name,
                "prompt_version": self.prompt_version,
                "content_markdown": self.content_markdown,
                "artifact_md_path": self.artifact_md_path,
                "status": self.status,
                "error_message": self.error_message,
            }
        )
        return data
