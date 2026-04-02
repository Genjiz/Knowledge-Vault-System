from app.extensions import db
from app.models.base import BaseModel


class CrawlTask(BaseModel):
    __tablename__ = "crawl_task"

    task_type = db.Column(db.String(50), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)
    journal_name = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    issue = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="pending")
    progress_message = db.Column(db.Text)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    logs = db.relationship(
        "CrawlTaskLog",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    raw_issues = db.relationship("RawIssue", back_populates="crawl_task", lazy="selectin")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "task_type": self.task_type,
                "source_type": self.source_type,
                "journal_name": self.journal_name,
                "year": self.year,
                "issue": self.issue,
                "status": self.status,
                "progress_message": self.progress_message,
                "error_message": self.error_message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            }
        )
        return data
