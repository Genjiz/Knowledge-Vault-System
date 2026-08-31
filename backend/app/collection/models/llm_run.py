from app.core.extensions import db
from app.papers.models.base import BaseModel


class LLMRun(BaseModel):
    __tablename__ = "llm_run"

    run_type = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    model_name = db.Column(db.String(100))
    status = db.Column(db.String(32), nullable=False, default="pending")
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    raw_paper_id = db.Column(db.Integer, db.ForeignKey("raw_paper.id"), index=True)
    raw_issue_analysis_id = db.Column(
        db.Integer, db.ForeignKey("raw_issue_analysis.id"), index=True
    )

    raw_paper = db.relationship("RawPaper", back_populates="llm_runs")
    raw_issue_analysis = db.relationship("RawIssueAnalysis", back_populates="llm_runs")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "run_type": self.run_type,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "model_name": self.model_name,
                "status": self.status,
                "error_message": self.error_message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
                "raw_paper_id": self.raw_paper_id,
                "raw_issue_analysis_id": self.raw_issue_analysis_id,
            }
        )
        return data
