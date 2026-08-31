from app.core.extensions import db
from app.papers.models.base import BaseModel


class CrawlTaskLog(BaseModel):
    __tablename__ = "crawl_task_log"

    task_id = db.Column(db.Integer, db.ForeignKey("crawl_task.id"), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.Text, nullable=False)

    task = db.relationship("CrawlTask", back_populates="logs")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "task_id": self.task_id,
                "level": self.level,
                "message": self.message,
            }
        )
        return data
