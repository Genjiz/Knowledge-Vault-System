import json
import shutil
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db


class VideoNoteExecutionServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_root = BACKEND_DIR / ".tmp-tests" / "video-note-services"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.app.config["VIDEO_NOTE_PROJECT_ROOT"] = str(self.temp_root)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_pipeline_writes_paths_and_marks_task_completed(self):
        from app.video_notes.services.execution_service import ExecutionService
        from app.video_notes.services.task_service import TaskService
        from app.video_notes.repositories.task_repo import TaskRepository

        class FakeDownloadService:
            def download_audio(self, source_url, output_path):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"fake-wav")
                return {"audio_path": str(output_path), "video_title": "测试标题"}

        class FakeTranscriptionService:
            def transcribe_audio(self, audio_path, transcript_path, **kwargs):
                transcript_path.parent.mkdir(parents=True, exist_ok=True)
                transcript_path.write_text("1\n00:00:00,000 --> 00:00:01,000\n测试字幕\n", encoding="utf-8")
                return str(transcript_path)

        class FakeNoteGenerationService:
            def generate_note(self, *, transcript_text, source_url, bvid, video_title):
                return f"# {video_title}\n\n- {bvid}\n- {source_url}\n- {transcript_text.strip()}"

        task_service = TaskService()
        task_repo = TaskRepository()
        task = task_service.create_task(
            source_url="https://www.bilibili.com/video/BV1qdXoBdEYy/",
            platform="bilibili",
            bvid="BV1qdXoBdEYy",
        )

        execution_service = ExecutionService(
            download_service=FakeDownloadService(),
            transcription_service=FakeTranscriptionService(),
            note_generation_service=FakeNoteGenerationService(),
        )
        execution_service.run_task(task.id)
        refreshed = task_repo.get_by_id(task.id)

        self.assertEqual(refreshed.status, "completed")
        self.assertEqual(refreshed.current_step, "done")
        self.assertTrue(Path(refreshed.audio_path).exists())
        self.assertTrue(Path(refreshed.transcript_path).exists())
        self.assertTrue(Path(refreshed.note_path).exists())
        self.assertTrue(Path(refreshed.metadata_path).exists())

        metadata = json.loads(Path(refreshed.metadata_path).read_text(encoding="utf-8"))
        self.assertEqual(metadata["task_id"], task.id)
        self.assertEqual(metadata["bvid"], "BV1qdXoBdEYy")
        self.assertEqual(metadata["status"], "completed")

    def test_pipeline_marks_task_failed_when_download_raises(self):
        from app.video_notes.services.execution_service import ExecutionService
        from app.video_notes.services.task_service import TaskService
        from app.video_notes.repositories.task_repo import TaskRepository

        class ExplodingDownloadService:
            def download_audio(self, source_url, output_path):
                raise RuntimeError("yt-dlp missing")

        task_service = TaskService()
        task_repo = TaskRepository()
        task = task_service.create_task(
            source_url="https://www.bilibili.com/video/BV1qdXoBdEYy/",
            platform="bilibili",
            bvid="BV1qdXoBdEYy",
        )

        execution_service = ExecutionService(download_service=ExplodingDownloadService())
        execution_service.run_task(task.id)
        refreshed = task_repo.get_by_id(task.id)

        self.assertEqual(refreshed.status, "failed")
        self.assertEqual(refreshed.current_step, "download_audio")
        self.assertIn("yt-dlp missing", refreshed.error_message)
        self.assertGreaterEqual(len(refreshed.logs), 1)


if __name__ == "__main__":
    unittest.main()
