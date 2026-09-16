import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.video_notes.runtime.bilibili import extract_bvid, resolve_video_title
from app.video_notes.runtime.paths import build_task_paths


class VideoNoteRuntimeTestCase(unittest.TestCase):
    def test_extract_bvid_from_standard_url(self):
        self.assertEqual(
            extract_bvid("https://www.bilibili.com/video/BV1qdXoBdEYy/"),
            "BV1qdXoBdEYy",
        )

    def test_title_falls_back_to_bvid_and_url(self):
        title = resolve_video_title(
            "",
            "BV1qdXoBdEYy",
            "https://www.bilibili.com/video/BV1qdXoBdEYy/",
        )

        self.assertIn("BV1qdXoBdEYy", title)
        self.assertIn("https://www.bilibili.com/video/BV1qdXoBdEYy/", title)

    def test_task_paths_live_under_data_artifacts(self):
        import os

        os.environ["DATA_ROOT"] = "C:/demo-data"
        try:
            paths = build_task_paths(task_id=12)

            base = Path("C:/demo-data/artifacts/video-notes/12")
            self.assertEqual(paths["task_root"], base)
            self.assertEqual(paths["audio"], base / "source" / "video.wav")
            self.assertEqual(paths["transcript"], base / "transcript" / "video.srt")
            self.assertEqual(paths["note"], base / "notes" / "final-note.md")
            self.assertEqual(paths["metadata"], base / "metadata.json")
        finally:
            os.environ.pop("DATA_ROOT", None)


if __name__ == "__main__":
    unittest.main()
