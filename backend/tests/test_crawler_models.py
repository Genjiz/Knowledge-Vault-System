import unittest
from pathlib import Path
import sys
import tempfile
import tempfile

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class CrawlerModelRegistrationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def test_crawler_models_are_importable_from_app_models(self):
        from app.papers.models import (  # noqa: F401
            CrawlTask,
            CrawlTaskLog,
            LLMRun,
            RawIssue,
            RawIssueAnalysis,
            RawPaper,
        )

        db.create_all()

        self.assertIn("crawl_task", db.metadata.tables)
        self.assertIn("crawl_task_log", db.metadata.tables)
        self.assertIn("raw_issue", db.metadata.tables)
        self.assertIn("raw_paper", db.metadata.tables)
        self.assertIn("raw_issue_analysis", db.metadata.tables)
        self.assertIn("llm_run", db.metadata.tables)


if __name__ == "__main__":
    unittest.main()
