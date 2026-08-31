import os
import shutil
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class VideoNoteApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_root = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "video-note-api"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self._original_data_root = os.environ.get("DATA_ROOT")
        os.environ["DATA_ROOT"] = str(self.temp_root)
        self.app.config["VIDEO_NOTE_TASK_EXECUTOR"] = lambda task_id: None
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self._original_data_root is None:
            os.environ.pop("DATA_ROOT", None)
        else:
            os.environ["DATA_ROOT"] = self._original_data_root
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_create_video_note_task_returns_task_payload(self):
        response = self.client.post(
            "/api/video-note-tasks",
            json={"source_url": "https://www.bilibili.com/video/BV1qdXoBdEYy/"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["bvid"], "BV1qdXoBdEYy")

    def test_create_video_note_task_rejects_invalid_url(self):
        response = self.client.post(
            "/api/video-note-tasks",
            json={"source_url": "https://example.com/not-bilibili"},
        )

        self.assertEqual(response.status_code, 400)

    def test_list_video_note_tasks_returns_created_task(self):
        create_response = self.client.post(
            "/api/video-note-tasks",
            json={"source_url": "https://www.bilibili.com/video/BV1qdXoBdEYy/"},
        )
        task_id = create_response.get_json()["data"]["id"]

        list_response = self.client.get("/api/video-note-tasks")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.get_json()["data"][0]["id"], task_id)

        detail_response = self.client.get(f"/api/video-note-tasks/{task_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.get_json()["data"]["id"], task_id)

        logs_response = self.client.get(f"/api/video-note-tasks/{task_id}/logs")
        self.assertEqual(logs_response.status_code, 200)
        self.assertEqual(logs_response.get_json()["data"], [])

    def test_detail_returns_transcript_and_note_preview_when_files_exist(self):
        from app.video_notes.repositories.task_repo import TaskRepository

        transcript_path = self.temp_root / "artifacts" / "video-notes" / "1" / "transcript" / "video.srt"
        note_path = self.temp_root / "artifacts" / "video-notes" / "1" / "notes" / "final-note.md"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text("1\n00:00:00,000 --> 00:00:01,000\n测试字幕\n", encoding="utf-8")
        note_path.write_text("# 测试笔记\n\n正文", encoding="utf-8")

        task = TaskRepository().create(
            source_url="https://www.bilibili.com/video/BV1qdXoBdEYy/",
            platform="bilibili",
            bvid="BV1qdXoBdEYy",
            video_title="测试标题",
            status="completed",
            current_step="done",
            transcript_path=str(transcript_path),
            note_path=str(note_path),
        )

        detail_response = self.client.get(f"/api/video-note-tasks/{task.id}")
        self.assertEqual(detail_response.status_code, 200)
        payload = detail_response.get_json()["data"]
        self.assertEqual(payload["transcript_content"], "1\n00:00:00,000 --> 00:00:01,000\n测试字幕\n")
        self.assertEqual(payload["note_content"], "# 测试笔记\n\n正文")


if __name__ == "__main__":
    unittest.main()
