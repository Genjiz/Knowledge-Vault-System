from app.video_notes.repositories.task_repo import TaskRepository


class TaskService:
    def __init__(self, task_repo=None):
        self.task_repo = task_repo or TaskRepository()

    def create_task(self, **kwargs):
        return self.task_repo.create(**kwargs)

    def append_log(self, task, message, level="info"):
        return self.task_repo.add_log(task=task, message=message, level=level)

    def update_task(self, task_id, **kwargs):
        return self.task_repo.update(task_id, **kwargs)
