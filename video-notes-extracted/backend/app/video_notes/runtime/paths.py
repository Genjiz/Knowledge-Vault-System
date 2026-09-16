from pathlib import Path

from app.core.paths import video_note_task_root


def build_task_paths(task_id):
    task_root = video_note_task_root(task_id)
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
