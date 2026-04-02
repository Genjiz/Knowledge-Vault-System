from pathlib import Path


def build_task_paths(project_root, task_id):
    task_root = Path(project_root) / "backend" / "artifacts" / "video-notes" / str(task_id)
    return {
        "task_root": task_root,
        "source_dir": task_root / "source",
        "transcript_dir": task_root / "transcript",
        "notes_dir": task_root / "notes",
        "audio": task_root / "source" / "video.wav",
        "transcript": task_root / "transcript" / "video.srt",
        "note": task_root / "notes" / "final-note.md",
        "metadata": task_root / "metadata.json",
    }
