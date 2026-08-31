from app.collection.models import CrawlTask, CrawlTaskLog
from app.core.extensions import db
from app.papers.repositories.base import BaseRepository


class TaskRepository(BaseRepository):
    model = CrawlTask

    def add_log(self, task, message, level="info"):
        log = CrawlTaskLog(task_id=task.id, message=message, level=level)
        db.session.add(log)
        db.session.commit()
        return log
