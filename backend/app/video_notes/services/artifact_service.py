import json
from pathlib import Path

from flask import current_app

from app.crawler.runtime.paths import get_project_root
from app.video_notes.runtime.paths import build_task_paths


class ArtifactService:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else None

    def _project_root(self):
        if self.project_root:
            return self.project_root

        configured_root = current_app.config.get("VIDEO_NOTE_PROJECT_ROOT")
        if configured_root:
            return Path(configured_root)

        return get_project_root()

    def task_paths(self, task_id):
        return build_task_paths(self._project_root(), task_id)

    def prepare_task_dirs(self, task_id):
        paths = self.task_paths(task_id)
        paths["source_dir"].mkdir(parents=True, exist_ok=True)
        paths["transcript_dir"].mkdir(parents=True, exist_ok=True)
        paths["notes_dir"].mkdir(parents=True, exist_ok=True)
        return paths

    def write_note(self, task_id, content):
        paths = self.prepare_task_dirs(task_id)
        paths["note"].write_text(content or "", encoding="utf-8")
        return str(paths["note"])

    def write_metadata(self, task):
        paths = self.prepare_task_dirs(task.id)
        payload = task.to_dict()
        payload["task_id"] = task.id
        paths["metadata"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(paths["metadata"])
