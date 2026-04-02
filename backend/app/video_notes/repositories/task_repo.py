from app.extensions import db
from app.repositories.base import BaseRepository
from app.video_notes.models import VideoNoteTask, VideoNoteTaskLog


class TaskRepository(BaseRepository):
    model = VideoNoteTask

    def get_all(self):
        return self.model.query.order_by(self.model.created_at.desc(), self.model.id.desc()).all()

    def add_log(self, task, message, level="info"):
        log = VideoNoteTaskLog(task_id=task.id, message=message, level=level)
        db.session.add(log)
        db.session.commit()
        return log
