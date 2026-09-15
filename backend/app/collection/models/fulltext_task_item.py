from app.core.extensions import db
from app.papers.models.base import BaseModel


class FullTextTaskItem(BaseModel):
    __tablename__ = "fulltext_task_item"

    task_id = db.Column(
        db.Integer,
        db.ForeignKey("fulltext_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    literature_id = db.Column(
        db.Integer,
        db.ForeignKey("literature.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_paper_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_paper.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type = db.Column(db.String(50), nullable=False)
    source_url = db.Column(db.String(1000))
    action_url = db.Column(db.String(1000))
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    failure_code = db.Column(db.String(50), index=True)
    error_message = db.Column(db.Text)
    pdf_path = db.Column(db.String(500))
    file_size_bytes = db.Column(db.BigInteger)
    sha256 = db.Column(db.String(64))
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    task = db.relationship("FullTextTask", back_populates="items")
    literature = db.relationship("Literature", back_populates="fulltext_task_items")
    raw_paper = db.relationship("RawPaper", back_populates="fulltext_task_items")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "task_id": self.task_id,
                "literature_id": self.literature_id,
                "literature_title": self.literature.title if self.literature else None,
                "raw_paper_id": self.raw_paper_id,
                "source_type": self.source_type,
                "source_url": self.source_url,
                "action_url": self.action_url,
                "status": self.status,
                "failure_code": self.failure_code,
                "error_message": self.error_message,
                "pdf_path": self.pdf_path,
                "file_size_bytes": self.file_size_bytes,
                "sha256": self.sha256,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            }
        )
        return data
