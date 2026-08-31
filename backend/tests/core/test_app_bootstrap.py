import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class AppBootstrapTestCase(unittest.TestCase):
    def test_factory_boots_and_models_create_crawler_tables(self):
        app = create_app("testing")

        with app.app_context():
            db.create_all()
            table_names = {
                row[0]
                for row in db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
            }

        self.assertIn("crawl_task", table_names)
        self.assertIn("raw_issue", table_names)


if __name__ == "__main__":
    unittest.main()
