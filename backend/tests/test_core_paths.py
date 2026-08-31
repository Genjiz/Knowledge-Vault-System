import os
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class CorePathsTestCase(unittest.TestCase):
    def setUp(self):
        self._original_data_root = os.environ.get("DATA_ROOT")

    def tearDown(self):
        if self._original_data_root is None:
            os.environ.pop("DATA_ROOT", None)
        else:
            os.environ["DATA_ROOT"] = self._original_data_root

    def test_defaults_point_to_backend_data(self):
        from app.core import paths

        self.assertEqual(paths.data_root(), BACKEND_DIR / "data")
        self.assertEqual(paths.database_path(), BACKEND_DIR / "data" / "db" / "app.db")
        self.assertEqual(paths.upload_folder(), BACKEND_DIR / "data" / "uploads" / "pdfs")
        self.assertEqual(paths.artifacts_root(), BACKEND_DIR / "data" / "artifacts")
        self.assertEqual(paths.crawler_artifacts_root(), BACKEND_DIR / "data" / "artifacts" / "crawler")
        self.assertEqual(paths.video_notes_artifacts_root(), BACKEND_DIR / "data" / "artifacts" / "video-notes")

    def test_data_root_env_override_applies_to_all_paths(self):
        from app.core import paths

        os.environ["DATA_ROOT"] = "C:/demo-data"

        self.assertEqual(paths.data_root(), Path("C:/demo-data"))
        self.assertEqual(paths.database_path(), Path("C:/demo-data/db/app.db"))
        self.assertEqual(paths.upload_folder(), Path("C:/demo-data/uploads/pdfs"))
        self.assertEqual(paths.artifacts_root(), Path("C:/demo-data/artifacts"))
        self.assertEqual(paths.crawler_artifacts_root(), Path("C:/demo-data/artifacts/crawler"))
        self.assertEqual(paths.video_notes_artifacts_root(), Path("C:/demo-data/artifacts/video-notes"))

    def test_database_uri_uses_sqlite_prefix(self):
        from app.core import paths

        os.environ["DATA_ROOT"] = "C:/demo-data"

        self.assertEqual(paths.database_uri(), "sqlite:///C:/demo-data/db/app.db")

    def test_video_note_task_root_contains_task_id(self):
        from app.core import paths

        os.environ["DATA_ROOT"] = "C:/demo-data"

        self.assertEqual(paths.video_note_task_root(12), Path("C:/demo-data/artifacts/video-notes/12"))


if __name__ == "__main__":
    unittest.main()
