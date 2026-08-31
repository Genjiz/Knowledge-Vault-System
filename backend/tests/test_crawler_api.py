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


class CrawlerApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "api-artifacts"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.app.config["ARTIFACT_ROOT"] = str(self.temp_dir)
        self.ctx = self.app.app_context()
        self.ctx.push()
        from app.collection.models import RawIssue, RawPaper  # noqa: F401

        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _seed_issue(self):
        from app.collection.models import CrawlTask, RawIssue, RawPaper

        task = CrawlTask(
            task_type="crawl",
            source_type="foreign",
            journal_name="Information Processing & Management",
            year=2024,
            issue="6",
            status="completed",
        )
        db.session.add(task)
        db.session.flush()

        raw_issue = RawIssue(
            source_type="foreign",
            journal_name="Information Processing & Management",
            journal_slug="information-processing-and-management",
            year=2024,
            issue="6",
            volume="60",
            language="en",
            source_url="https://example.com/issue",
            paper_count=1,
            crawl_task_id=task.id,
            translation_status="pending",
            analysis_status="pending",
        )
        db.session.add(raw_issue)
        db.session.flush()

        db.session.add(
            RawPaper(
                raw_issue_id=raw_issue.id,
                title="Paper A",
                abstract="Abstract A",
                authors="Author One",
                sort_index=0,
            )
        )
        db.session.commit()
        return task, raw_issue

    def test_create_crawl_task_runs_ingestion(self):
        task, raw_issue = self._seed_issue()

        class FakeIngestionService:
            def run_ingestion(self, source_type, journal_name, year, issue):
                return task, raw_issue

        self.app.config["CRAWLER_INGESTION_SERVICE"] = FakeIngestionService()

        response = self.client.post(
            "/api/crawl-tasks",
            json={
                "source_type": "foreign",
                "journal_name": "Information Processing & Management",
                "year": 2024,
                "issue": "6",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["data"]["task"]["id"], task.id)
        self.assertEqual(payload["data"]["raw_issue"]["id"], raw_issue.id)

    def test_create_crawl_task_returns_error_response_when_provider_fails(self):
        from app.collection.sources.base import ProviderError

        class FakeIngestionService:
            def run_ingestion(self, source_type, journal_name, year, issue):
                raise ProviderError("Foreign crawl failed: browser connect error")

        self.app.config["CRAWLER_INGESTION_SERVICE"] = FakeIngestionService()

        response = self.client.post(
            "/api/crawl-tasks",
            json={
                "source_type": "foreign",
                "journal_name": "Information Processing & Management",
                "year": 2024,
                "issue": "6",
            },
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("browser connect error", response.get_json()["message"])

    def test_list_raw_issues_and_fetch_detail(self):
        _, raw_issue = self._seed_issue()

        response = self.client.get("/api/raw-issues")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["items"][0]["id"], raw_issue.id)

        detail = self.client.get(f"/api/raw-issues/{raw_issue.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["data"]["id"], raw_issue.id)

        papers = self.client.get(f"/api/raw-issues/{raw_issue.id}/papers")
        self.assertEqual(papers.status_code, 200)
        self.assertEqual(len(papers.get_json()["data"]), 1)

    def test_translate_and_analyze_endpoints_use_services(self):
        _, raw_issue = self._seed_issue()

        class FakeTranslationService:
            def translate_issue(self, raw_issue_id):
                from app.collection.models import RawIssue

                issue = db.session.get(RawIssue, raw_issue_id)
                issue.translation_status = "completed"
                db.session.commit()
                return issue

        class FakeAnalysisService:
            def analyze_issue(self, raw_issue_id):
                from app.collection.models import RawIssueAnalysis

                analysis = RawIssueAnalysis(
                    raw_issue_id=raw_issue_id,
                    model_name="fake-gemini",
                    content_markdown="# Analysis",
                    status="completed",
                )
                db.session.add(analysis)
                db.session.commit()
                return analysis

        self.app.config["CRAWLER_TRANSLATION_SERVICE"] = FakeTranslationService()
        self.app.config["CRAWLER_ANALYSIS_SERVICE"] = FakeAnalysisService()

        translate = self.client.post(f"/api/raw-issues/{raw_issue.id}/translate")
        self.assertEqual(translate.status_code, 200)
        self.assertEqual(translate.get_json()["data"]["translation_status"], "completed")

        analyze = self.client.post(f"/api/raw-issues/{raw_issue.id}/analyze")
        self.assertEqual(analyze.status_code, 200)
        self.assertEqual(analyze.get_json()["data"]["status"], "completed")

        analysis = self.client.get(f"/api/raw-issues/{raw_issue.id}/analysis")
        self.assertEqual(analysis.status_code, 200)
        self.assertEqual(analysis.get_json()["data"]["content_markdown"], "# Analysis")

    def test_translate_and_analyze_return_error_response_when_provider_fails(self):
        from app.collection.sources.base import ProviderError

        _, raw_issue = self._seed_issue()

        class FakeTranslationService:
            def translate_issue(self, raw_issue_id):
                raise ProviderError("google-genai is not installed")

        class FakeAnalysisService:
            def analyze_issue(self, raw_issue_id):
                raise ProviderError("analysis request failed")

        self.app.config["CRAWLER_TRANSLATION_SERVICE"] = FakeTranslationService()
        self.app.config["CRAWLER_ANALYSIS_SERVICE"] = FakeAnalysisService()

        translate = self.client.post(f"/api/raw-issues/{raw_issue.id}/translate")
        self.assertEqual(translate.status_code, 502)
        self.assertIn("google-genai is not installed", translate.get_json()["message"])

        analyze = self.client.post(f"/api/raw-issues/{raw_issue.id}/analyze")
        self.assertEqual(analyze.status_code, 502)
        self.assertIn("analysis request failed", analyze.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
