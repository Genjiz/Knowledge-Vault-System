from datetime import UTC, datetime
from pathlib import Path

from app.video_notes.repositories.task_repo import TaskRepository
from app.video_notes.runtime.bilibili import resolve_video_title
from app.video_notes.services.artifact_service import ArtifactService
from app.video_notes.services.download_service import DownloadService
from app.video_notes.services.note_generation_service import NoteGenerationService
from app.video_notes.services.task_service import TaskService
from app.video_notes.services.transcription_service import TranscriptionService


class ExecutionService:
    def __init__(
        self,
        task_repo=None,
        task_service=None,
        artifact_service=None,
        download_service=None,
        transcription_service=None,
        note_generation_service=None,
    ):
        self.task_repo = task_repo or TaskRepository()
        self.task_service = task_service or TaskService(task_repo=self.task_repo)
        self.artifact_service = artifact_service or ArtifactService()
        self.download_service = download_service or DownloadService()
        self.transcription_service = transcription_service or TranscriptionService()
        self.note_generation_service = note_generation_service or NoteGenerationService()

    def run_task(self, task_id):
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Video note task {task_id} not found")

        paths = self.artifact_service.prepare_task_dirs(task.id)
        self.task_service.update_task(task.id, metadata_path=str(paths["metadata"]))

        try:
            task = self.task_service.update_task(
                task.id,
                status="running",
                current_step="download_audio",
                progress_message="Downloading audio",
                error_message=None,
                started_at=datetime.now(UTC),
            )
            self.task_service.append_log(task, "Starting audio download")

            download_result = self.download_service.download_audio(task.source_url, paths["audio"])
            audio_path = Path(download_result.get("audio_path") or paths["audio"])
            video_title = resolve_video_title(download_result.get("video_title"), task.bvid, task.source_url)
            task = self.task_service.update_task(
                task.id,
                audio_path=str(audio_path),
                video_title=video_title,
                progress_message="Audio download completed",
            )
            self.task_service.append_log(task, "Audio download completed")

            task = self.task_service.update_task(
                task.id,
                current_step="transcribe_srt",
                progress_message="Transcribing subtitle",
            )
            self.task_service.append_log(task, "Starting whisper transcription")
            transcript_path = Path(
                self.transcription_service.transcribe_audio(
                    audio_path,
                    paths["transcript"],
                    whisper_model=task.whisper_model,
                    language=task.language,
                    device=task.device,
                    compute_type=task.compute_type,
                    use_vad=task.use_vad,
                )
            )
            task = self.task_service.update_task(
                task.id,
                transcript_path=str(transcript_path),
                progress_message="Transcription completed",
            )
            self.task_service.append_log(task, "Whisper transcription completed")

            task = self.task_service.update_task(
                task.id,
                current_step="generate_note",
                progress_message="Generating Markdown note",
            )
            self.task_service.append_log(task, "Starting note generation")
            transcript_text = transcript_path.read_text(encoding="utf-8")
            markdown = self.note_generation_service.generate_note(
                transcript_text=transcript_text,
                source_url=task.source_url,
                bvid=task.bvid,
                video_title=task.video_title,
                profile_id=task.profile_id,
            )
            note_path = self.artifact_service.write_note(task.id, markdown)
            task = self.task_service.update_task(
                task.id,
                note_path=note_path,
                status="completed",
                current_step="done",
                progress_message="Video note completed",
                finished_at=datetime.now(UTC),
            )
            self.task_service.append_log(task, "Video note task completed")
        except Exception as exc:
            task = self.task_service.update_task(
                task.id,
                status="failed",
                error_message=str(exc),
                finished_at=datetime.now(UTC),
            )
            self.task_service.append_log(task, f"Task failed: {exc}", level="error")

        task = self.task_repo.get_by_id(task.id)
        metadata_path = self.artifact_service.write_metadata(task)
        task = self.task_service.update_task(task.id, metadata_path=metadata_path)
        return task
