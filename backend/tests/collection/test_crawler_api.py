import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
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
        from app.core.llm.models import LLMProfile

        profile = LLMProfile(
            name="测试模型",
            protocol="gemini",
            model_name="gemini-test",
            enabled=True,
        )
        db.session.add(profile)
        db.session.commit()
        self.profile_id = profile.id
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

    def test_create_crawl_task_can_schedule_fulltext_as_second_stage(self):
        task, raw_issue = self._seed_issue()
        task.source_type = "magtech"
        raw_issue.source_type = "magtech"
        db.session.commit()

        class FakeIngestionService:
            def run_ingestion(self, source_type, journal_name, year, issue):
                return task, raw_issue

        class FakeTask:
            id = 77

            def to_dict(self):
                return {"id": self.id, "mode": "after_ingestion", "status": "pending"}

        class FakeFullTextService:
            def create_issue_task(self, raw_issue_id, mode="issue"):
                self.raw_issue_id = raw_issue_id
                self.mode = mode
                return FakeTask()

        fulltext_service = FakeFullTextService()
        scheduled = []
        self.app.config["CRAWLER_INGESTION_SERVICE"] = FakeIngestionService()
        self.app.config["FULLTEXT_SERVICE"] = fulltext_service
        self.app.config["FULLTEXT_TASK_EXECUTOR"] = scheduled.append

        response = self.client.post(
            "/api/crawl-tasks",
            json={
                "source_type": "magtech",
                "journal_name": "情报学报",
                "year": 2026,
                "issue": "7",
                "download_fulltext": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["fulltext_task"]["mode"], "after_ingestion")
        self.assertEqual(fulltext_service.raw_issue_id, raw_issue.id)
        self.assertEqual(fulltext_service.mode, "after_ingestion")
        self.assertEqual(scheduled, [77])

    def test_create_crawl_task_rejects_fulltext_for_unsupported_source(self):
        response = self.client.post(
            "/api/crawl-tasks",
            json={
                "source_type": "ncpssd",
                "journal_name": "情报学报",
                "year": 2026,
                "issue": "7",
                "download_fulltext": True,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不支持全文", response.get_json()["message"])

    def test_create_year_scope_task_does_not_require_issue(self):
        task, raw_issue = self._seed_issue()
        task.source_type = "scopus"
        task.issue = "year"
        raw_issue.source_type = "scopus"
        raw_issue.issue = "year"
        db.session.commit()
        calls = []

        class FakeIngestionService:
            def run_ingestion(self, source_type, journal_name, year, issue):
                calls.append((source_type, journal_name, year, issue))
                return task, [raw_issue]

        self.app.config["CRAWLER_INGESTION_SERVICE"] = FakeIngestionService()
        response = self.client.post(
            "/api/crawl-tasks",
            json={
                "source_type": "scopus",
                "journal_name": "Information Processing & Management",
                "year": 2025,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[0][-1], "year")
        payload = response.get_json()["data"]
        self.assertEqual([item["id"] for item in payload["raw_issues"]], [raw_issue.id])
        self.assertEqual(payload["raw_issue"]["id"], raw_issue.id)

    def test_create_scopus_task_rejects_fulltext(self):
        response = self.client.post(
            "/api/crawl-tasks",
            json={
                "source_type": "scopus",
                "journal_name": "IP&M",
                "year": 2025,
                "download_fulltext": True,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不支持全文", response.get_json()["message"])

    def test_create_issue_scope_task_still_requires_issue(self):
        response = self.client.post(
            "/api/crawl-tasks",
            json={"source_type": "elsevier", "journal_name": "IP&M", "year": 2025},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("issue", response.get_json()["message"])

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
        from app.collection.pipeline.paper_merge import PaperMergeService

        _, raw_issue = self._seed_issue()
        raw_issue.expected_paper_count = 1
        raw_issue.paper_count = 2
        literature = PaperMergeService().upsert_raw_paper(raw_issue.papers[0])
        literature.pdf_path = "uploads/pdfs/1.pdf"
        db.session.commit()

        response = self.client.get("/api/raw-issues")
        self.assertEqual(response.status_code, 200)
        issue_payload = response.get_json()["data"]["items"][0]
        self.assertEqual(issue_payload["id"], raw_issue.id)
        self.assertEqual(issue_payload["expected_paper_count"], 1)
        self.assertEqual(issue_payload["title_collected_count"], 1)
        self.assertEqual(issue_payload["abstract_collected_count"], 1)
        self.assertEqual(issue_payload["fulltext_collected_count"], 1)

        detail = self.client.get(f"/api/raw-issues/{raw_issue.id}")
        self.assertEqual(detail.status_code, 200)
        detail_payload = detail.get_json()["data"]
        self.assertEqual(detail_payload["id"], raw_issue.id)
        self.assertEqual(detail_payload["papers"][0]["literature_id"], literature.id)
        self.assertEqual(detail_payload["papers"][0]["pdf_path"], "uploads/pdfs/1.pdf")

        papers = self.client.get(f"/api/raw-issues/{raw_issue.id}/papers")
        self.assertEqual(papers.status_code, 200)
        self.assertEqual(len(papers.get_json()["data"]), 1)

    def test_list_raw_issues_honors_pagination_parameters(self):
        from app.collection.models import RawIssue

        _, raw_issue = self._seed_issue()
        db.session.add(
            RawIssue(
                source_type=raw_issue.source_type,
                journal_name=raw_issue.journal_name,
                year=raw_issue.year,
                volume=raw_issue.volume,
                issue="4",
                region=raw_issue.region,
                paper_count=0,
            )
        )
        db.session.commit()

        response = self.client.get("/api/raw-issues?page=2&per_page=1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["per_page"], 1)
        self.assertEqual(payload["total"], 2)
        self.assertEqual(len(payload["items"]), 1)

    def test_translate_and_analyze_endpoints_use_services(self):
        _, raw_issue = self._seed_issue()

        class FakeTranslationService:
            def translate_issue(self, raw_issue_id, profile_id):
                self.profile_id = profile_id
                from app.collection.models import RawIssue

                issue = db.session.get(RawIssue, raw_issue_id)
                issue.translation_status = "completed"
                db.session.commit()
                return issue

        class FakeAnalysisService:
            def analyze_issue(self, raw_issue_id, profile_id):
                self.profile_id = profile_id
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

        translate = self.client.post(
            f"/api/raw-issues/{raw_issue.id}/translate",
            json={"profile_id": self.profile_id},
        )
        self.assertEqual(translate.status_code, 200)
        self.assertEqual(translate.get_json()["data"]["translation_status"], "completed")

        analyze = self.client.post(
            f"/api/raw-issues/{raw_issue.id}/analyze",
            json={"profile_id": self.profile_id},
        )
        self.assertEqual(analyze.status_code, 200)
        self.assertEqual(analyze.get_json()["data"]["status"], "completed")

        analysis = self.client.get(f"/api/raw-issues/{raw_issue.id}/analysis")
        self.assertEqual(analysis.status_code, 200)
        self.assertEqual(analysis.get_json()["data"]["content_markdown"], "# Analysis")

    def test_translate_and_analyze_return_error_response_when_provider_fails(self):
        from app.collection.sources.base import ProviderError

        _, raw_issue = self._seed_issue()

        class FakeTranslationService:
            def translate_issue(self, raw_issue_id, profile_id):
                raise ProviderError("google-genai is not installed")

        class FakeAnalysisService:
            def analyze_issue(self, raw_issue_id, profile_id):
                raise ProviderError("analysis request failed")

        self.app.config["CRAWLER_TRANSLATION_SERVICE"] = FakeTranslationService()
        self.app.config["CRAWLER_ANALYSIS_SERVICE"] = FakeAnalysisService()

        translate = self.client.post(
            f"/api/raw-issues/{raw_issue.id}/translate",
            json={"profile_id": self.profile_id},
        )
        self.assertEqual(translate.status_code, 502)
        self.assertIn("google-genai is not installed", translate.get_json()["message"])

        analyze = self.client.post(
            f"/api/raw-issues/{raw_issue.id}/analyze",
            json={"profile_id": self.profile_id},
        )
        self.assertEqual(analyze.status_code, 502)
        self.assertIn("analysis request failed", analyze.get_json()["message"])

    def test_llm_issue_actions_require_explicit_profile(self):
        _, raw_issue = self._seed_issue()

        translate = self.client.post(f"/api/raw-issues/{raw_issue.id}/translate", json={})
        analyze = self.client.post(f"/api/raw-issues/{raw_issue.id}/analyze", json={})

        self.assertEqual(translate.status_code, 400)
        self.assertEqual(analyze.status_code, 400)
        self.assertIn("模型", translate.get_json()["message"])

    def test_delete_raw_issue_preserves_literature_and_removes_artifact(self):
        from app.collection.pipeline.paper_merge import PaperMergeService
        from app.papers.models import Literature

        _, raw_issue = self._seed_issue()
        literature = PaperMergeService().upsert_raw_paper(raw_issue.papers[0])
        artifact_path = self.temp_dir / "raw-json" / "foreign" / "issue.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("{}", encoding="utf-8")
        raw_issue.raw_json_path = str(artifact_path)
        db.session.commit()

        response = self.client.delete(f"/api/raw-issues/{raw_issue.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(type(raw_issue), raw_issue.id))
        preserved = db.session.get(Literature, literature.id)
        self.assertIsNotNone(preserved)
        self.assertIsNone(preserved.source_raw_paper_id)
        self.assertFalse(artifact_path.exists())

    def test_delete_raw_issue_returns_404_for_missing_issue(self):
        response = self.client.delete("/api/raw-issues/99999")

        self.assertEqual(response.status_code, 404)

    def test_refresh_scopus_issue_runs_targeted_year_ingestion(self):
        task, raw_issue = self._seed_issue()
        task.source_type = "scopus"
        raw_issue.source_type = "scopus"
        raw_issue.volume = "63"
        raw_issue.issue = "2PA"
        db.session.commit()
        calls = []

        class FakeIngestionService:
            def run_ingestion(self, source_type, journal_name, year, issue, **kwargs):
                calls.append((source_type, journal_name, year, issue, kwargs))
                return task, [raw_issue]

        self.app.config["CRAWLER_INGESTION_SERVICE"] = FakeIngestionService()
        response = self.client.post(f"/api/raw-issues/{raw_issue.id}/refresh")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            calls,
            [("scopus", raw_issue.journal_name, raw_issue.year, "year", {
                "target_volume": "63",
                "target_issue": "2PA",
            })],
        )
        self.assertEqual(response.get_json()["data"]["raw_issues"][0]["id"], raw_issue.id)

    def test_refresh_issue_rejects_non_scopus_source(self):
        _, raw_issue = self._seed_issue()

        response = self.client.post(f"/api/raw-issues/{raw_issue.id}/refresh")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Scopus", response.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
