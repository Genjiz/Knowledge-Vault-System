import sys
import unittest
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db


class VideoNoteModelTestCase(unittest.TestCase):
    def test_create_app_creates_video_note_tables(self):
        app = create_app("testing")

        with app.app_context():
            table_names = {
                row[0]
                for row in db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
            }

        self.assertIn("video_note_task", table_names)
        self.assertIn("video_note_task_log", table_names)


if __name__ == "__main__":
    unittest.main()
