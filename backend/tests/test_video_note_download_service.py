import shutil
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class DownloadServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_root = BACKEND_DIR / ".tmp-tests" / "video-note-download-service"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_download_audio_disables_simulation_and_returns_title(self):
        from app.video_notes.services.download_service import DownloadService

        output_path = self.temp_root / "video.wav"
        expected_title = "测试标题"

        def fake_run(command, **kwargs):
            self.assertIn("--no-simulate", command)
            self.assertNotIn("encoding", kwargs)
            self.assertNotIn("text", kwargs)
            output_path.write_bytes(b"fake-wav")
            return SimpleNamespace(stdout=f"{expected_title}\n".encode("gb18030"), stderr=b"")

        service = DownloadService()
        with patch("app.video_notes.services.download_service.subprocess.run", side_effect=fake_run):
            result = service.download_audio("https://www.bilibili.com/video/BV1qdXoBdEYy/", output_path)

        self.assertEqual(result["audio_path"], str(output_path))
        self.assertEqual(result["video_title"], expected_title)


if __name__ == "__main__":
    unittest.main()
