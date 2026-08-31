import json
import shutil
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class IngestionWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "workflow-artifacts"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.app.config["ARTIFACT_ROOT"] = str(self.temp_dir)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_run_ingestion_creates_task_persists_issue_and_exports_json(self):
        from app.collection.services.ingestion_service import IngestionService

        class FakeProvider:
            def fetch_issue(self, journal_name, year, issue):
                return {
                    "issue": {
                        "source_type": "foreign",
                        "journal_name": journal_name,
                        "journal_slug": "information-processing-and-management",
                        "year": year,
                        "issue": issue,
                        "volume": "60",
                        "language": "en",
                        "source_url": "https://example.com/issue",
                    },
                    "papers": [
                        {
                            "title": "Paper A",
                            "authors": "Author One",
                            "abstract": "Abstract A",
                            "detail_url": "https://example.com/a",
                        }
                    ],
                }

        service = IngestionService(providers={"foreign": FakeProvider()})
        task, raw_issue = service.run_ingestion(
            source_type="foreign",
            journal_name="Information Processing & Management",
            year=2024,
            issue="6",
        )

        self.assertEqual(task.status, "completed")
        self.assertEqual(raw_issue.paper_count, 1)
        self.assertTrue(raw_issue.raw_json_path)
        payload = json.loads(Path(raw_issue.raw_json_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["papers"][0]["title"], "Paper A")
        self.assertEqual(len(task.logs), 2)

    def test_run_ingestion_marks_task_failed_when_provider_raises(self):
        from app.collection.sources.base import ProviderError
        from app.collection.services.ingestion_service import IngestionService
        from app.collection.models import CrawlTask

        class FakeProvider:
            def fetch_issue(self, journal_name, year, issue):
                raise ProviderError("Foreign crawl failed: browser connect error")

        service = IngestionService(providers={"foreign": FakeProvider()})

        with self.assertRaises(ProviderError):
            service.run_ingestion(
                source_type="foreign",
                journal_name="Information Processing & Management",
                year=2024,
                issue="6",
            )

        task = CrawlTask.query.order_by(CrawlTask.id.desc()).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.status, "failed")
        self.assertIn("browser connect error", task.error_message)
        self.assertEqual(len(task.logs), 2)


if __name__ == "__main__":
    unittest.main()
