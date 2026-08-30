import json

from app.video_notes.runtime.paths import build_task_paths


class ArtifactService:
    def task_paths(self, task_id):
        return build_task_paths(task_id)

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
