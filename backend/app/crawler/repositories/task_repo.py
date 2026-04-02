from app.crawler.models import CrawlTask, CrawlTaskLog
from app.extensions import db
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository):
    model = CrawlTask

    def add_log(self, task, message, level="info"):
        log = CrawlTaskLog(task_id=task.id, message=message, level=level)
        db.session.add(log)
        db.session.commit()
        return log
