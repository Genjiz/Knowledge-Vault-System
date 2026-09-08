from app.core.extensions import db
from app.papers.models.base import BaseModel


class FullTextTask(BaseModel):
    __tablename__ = "fulltext_task"

    mode = db.Column(db.String(32), nullable=False)
    source_type = db.Column(db.String(50), nullable=False, default="magtech")
    raw_issue_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_issue.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    replace_existing = db.Column(db.Boolean, nullable=False, default=False)
    total_count = db.Column(db.Integer, nullable=False, default=0)
    succeeded_count = db.Column(db.Integer, nullable=False, default=0)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
    skipped_count = db.Column(db.Integer, nullable=False, default=0)
    progress_message = db.Column(db.Text)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    raw_issue = db.relationship("RawIssue", back_populates="fulltext_tasks")
    items = db.relationship(
        "FullTextTaskItem",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="FullTextTaskItem.id.asc()",
    )

    def to_dict(self, include_items=True):
        data = super().to_dict()
        data.update(
            {
                "mode": self.mode,
                "source_type": self.source_type,
                "raw_issue_id": self.raw_issue_id,
                "status": self.status,
                "replace_existing": self.replace_existing,
                "total_count": self.total_count,
                "succeeded_count": self.succeeded_count,
                "failed_count": self.failed_count,
                "skipped_count": self.skipped_count,
                "progress_message": self.progress_message,
                "error_message": self.error_message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            }
        )
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data
