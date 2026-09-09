import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class CrawlerServiceSmokeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def test_can_create_task_and_persist_raw_issue_payload(self):
        from app.collection.services.ingestion_service import IngestionService
        from app.collection.services.task_service import TaskService

        task_service = TaskService()
        ingestion_service = IngestionService()

        task = task_service.create_task(
            task_type="crawl",
            source_type="foreign",
            journal_name="Information Processing & Management",
            year=2024,
            issue="6",
        )

        raw_issue = ingestion_service.save_issue_payload(
            task=task,
            issue_data={
                "source_type": "foreign",
                "journal_name": "Information Processing & Management",
                "journal_slug": "information-processing-and-management",
                "year": 2024,
                "issue": "6",
                "volume": "60",
                "language": "en",
                "source_url": "https://example.com/issue",
                "paper_count_hint": 1,
            },
            papers=[
                {
                    "title": "Paper A",
                    "authors": "Author One",
                    "abstract": "Abstract A",
                    "detail_url": "https://example.com/a",
                    "sort_index": 0,
                },
                {
                    "title": "Paper B",
                    "authors": "Author Two",
                    "abstract": "Abstract B",
                    "detail_url": "https://example.com/b",
                    "sort_index": 1,
                },
            ],
        )

        self.assertEqual(task.status, "pending")
        self.assertEqual(raw_issue.crawl_task_id, task.id)
        self.assertEqual(raw_issue.expected_paper_count, 1)
        self.assertEqual(raw_issue.paper_count, 2)
        self.assertEqual(len(raw_issue.papers), 2)
        self.assertEqual(raw_issue.papers[0].title, "Paper A")
        self.assertEqual(raw_issue.papers[1].sort_index, 1)


if __name__ == "__main__":
    unittest.main()
