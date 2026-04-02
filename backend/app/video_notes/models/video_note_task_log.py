from app.extensions import db
from app.models.base import BaseModel


class VideoNoteTaskLog(BaseModel):
    __tablename__ = "video_note_task_log"

    task_id = db.Column(db.Integer, db.ForeignKey("video_note_task.id"), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.Text, nullable=False)

    task = db.relationship("VideoNoteTask", back_populates="logs")

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
