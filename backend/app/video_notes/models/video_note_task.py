from app.extensions import db
from app.models.base import BaseModel


class VideoNoteTask(BaseModel):
    __tablename__ = "video_note_task"

    source_url = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(50), nullable=False, default="bilibili")
    bvid = db.Column(db.String(64), nullable=False, index=True)
    video_title = db.Column(db.String(500))
    status = db.Column(db.String(32), nullable=False, default="pending")
    current_step = db.Column(db.String(64))
    progress_message = db.Column(db.Text)
    error_message = db.Column(db.Text)

    whisper_model = db.Column(db.String(100), nullable=False, default="large-v3-turbo")
    language = db.Column(db.String(32), nullable=False, default="zh")
    device = db.Column(db.String(32), nullable=False, default="cuda")
    compute_type = db.Column(db.String(32), nullable=False, default="int8_float16")
    use_vad = db.Column(db.Boolean, nullable=False, default=True)

    audio_path = db.Column(db.Text)
    transcript_path = db.Column(db.Text)
    note_path = db.Column(db.Text)
    metadata_path = db.Column(db.Text)

    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    logs = db.relationship(
        "VideoNoteTaskLog",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "source_url": self.source_url,
                "platform": self.platform,
                "bvid": self.bvid,
                "video_title": self.video_title,
                "status": self.status,
                "current_step": self.current_step,
                "progress_message": self.progress_message,
                "error_message": self.error_message,
                "whisper_model": self.whisper_model,
                "language": self.language,
                "device": self.device,
                "compute_type": self.compute_type,
                "use_vad": self.use_vad,
                "audio_path": self.audio_path,
                "transcript_path": self.transcript_path,
                "note_path": self.note_path,
                "metadata_path": self.metadata_path,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            }
        )
        return data
