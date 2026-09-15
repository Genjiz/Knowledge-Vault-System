import json
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
                            "source_ref_json": json.dumps({"article_id": "1044"}),
                        }
                    ],
                }

        service = IngestionService(providers={"foreign": FakeProvider()})
        task, raw_issues = service.run_ingestion(
            source_type="foreign",
            journal_name="Information Processing & Management",
            year=2024,
            issue="6",
        )
        raw_issue = raw_issues[0]

        self.assertEqual(task.status, "completed")
        self.assertEqual(raw_issue.paper_count, 1)
        self.assertTrue(raw_issue.raw_json_path)
        payload = json.loads(Path(raw_issue.raw_json_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["papers"][0]["title"], "Paper A")
        self.assertEqual(
            json.loads(raw_issue.papers[0].source_ref_json),
            {"article_id": "1044"},
        )
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

    def test_recollecting_same_issue_replaces_links_without_stale_provenance(self):
        from app.collection.models import LiteratureSource
        from app.collection.services.ingestion_service import IngestionService
        from app.papers.models import Literature

        class MutableProvider:
            region = "domestic"

            def __init__(self):
                self.papers = [
                    {"title": "保留论文", "authors": "作者甲", "doi": "10.1/keep"},
                    {"title": "移除论文", "authors": "作者乙", "doi": "10.1/remove"},
                ]

            def fetch_issue(self, journal_name, year, issue):
                return {
                    "issue": {
                        "source_type": "magtech",
                        "region": "domestic",
                        "journal_name": journal_name,
                        "year": year,
                        "issue": issue,
                    },
                    "papers": self.papers,
                }

        provider = MutableProvider()
        service = IngestionService(providers={"magtech": provider})
        _, first_issues = service.run_ingestion("magtech", "情报学报", 2026, "3")
        first_issue = first_issues[0]
        removed = Literature.query.filter_by(title="移除论文").one()
        retained = Literature.query.filter_by(title="保留论文").one()
        original_raw_paper_id = retained.collection_sources[0].raw_paper_id
        retained.pdf_path = f"uploads/pdfs/{retained.id}.pdf"
        retained.pdf_source_type = "magtech"
        retained.pdf_source_raw_paper_id = original_raw_paper_id
        db.session.commit()

        provider.papers = [
            {"title": "保留论文", "authors": "官网修订作者", "doi": "10.1/keep"}
        ]
        _, second_issues = service.run_ingestion("magtech", "情报学报", 2026, "3")
        second_issue = second_issues[0]
        db.session.refresh(removed)

        self.assertEqual(first_issue.id, second_issue.id)
        self.assertEqual(second_issue.paper_count, 1)
        self.assertEqual(LiteratureSource.query.count(), 1)
        self.assertIsNone(removed.source_raw_paper_id)
        retained = Literature.query.filter_by(title="保留论文").one()
        self.assertEqual(retained.authors, "官网修订作者")
        self.assertEqual(retained.pdf_path, f"uploads/pdfs/{retained.id}.pdf")
        self.assertEqual(retained.pdf_source_type, "magtech")
        self.assertIsNone(retained.pdf_source_raw_paper_id)

    def test_source_priority_places_other_sources_below_ncpssd(self):
        from app.collection.sources.registry import source_priority

        self.assertGreater(source_priority("ncpssd"), source_priority("elsevier"))

    def test_year_ingestion_splits_papers_by_volume_and_issue(self):
        from app.collection.services.ingestion_service import IngestionService
        from app.papers.models import Journal

        journal = Journal(
            name="Information Processing & Management",
            issn="0306-4573",
            region="foreign",
        )
        db.session.add(journal)
        db.session.commit()
        calls = []

        class FakeYearProvider:
            source_id = "scopus"
            region = "foreign"
            ingest_scope = "year"

            def fetch_issue(self, journal_name, year, issue, **kwargs):
                calls.append((journal_name, year, issue, kwargs))
                return {
                    "issue": {
                        "source_type": "scopus",
                        "region": "foreign",
                        "journal_name": journal_name,
                        "year": year,
                        "issue": "year",
                        "volume": None,
                        "paper_count_hint": 3,
                        "language": "en",
                    },
                    "papers": [
                        {
                            "source_identifier": "2-s2.0-TEST001",
                            "source_ref_json": json.dumps(
                                {"eid": "2-s2.0-TEST001", "doi": "10.1/test"}
                            ),
                            "title": "Volume 62 issue 2PA",
                            "authors": "Test Author",
                            "doi": "10.1/test",
                            "volume": "62",
                            "issue": "2PA",
                        },
                        {
                            "source_identifier": "2-s2.0-TEST002",
                            "source_ref_json": json.dumps({"eid": "2-s2.0-TEST002"}),
                            "title": "Volume 63 issue 2PA",
                            "authors": "Test Author",
                            "volume": "63",
                            "issue": "2PA",
                        },
                        {
                            "source_identifier": "2-s2.0-TEST003",
                            "source_ref_json": json.dumps({"eid": "2-s2.0-TEST003"}),
                            "title": "Unassigned paper",
                            "authors": "Test Author",
                            "volume": "63",
                            "issue": None,
                        },
                    ],
                }

        service = IngestionService(providers={"scopus": FakeYearProvider()})
        task, raw_issues = service.run_ingestion(
            "scopus", journal.name, 2025, "ignored-client-value"
        )

        self.assertEqual(calls[0][-1], {"issn": "0306-4573"})
        self.assertEqual(calls[0][2], "year")
        self.assertEqual(task.issue, "year")
        self.assertEqual(
            [(item.volume, item.issue, item.paper_count) for item in raw_issues],
            [("62", "2PA", 1), ("63", "2PA", 1), ("63", "unassigned", 1)],
        )
        self.assertEqual(len(task.raw_issues), 3)
        literature = raw_issues[0].papers[0].literature_sources[0].literature
        self.assertEqual(literature.volume, "62")
        self.assertEqual(literature.issue, "2PA")
        self.assertEqual(literature.doi, "10.1/test")

    def test_targeted_year_refresh_replaces_only_requested_volume_issue(self):
        from app.collection.services.ingestion_service import IngestionService
        from app.papers.models import Journal

        journal = Journal(name="IP&M", issn="0306-4573", region="foreign")
        db.session.add(journal)
        db.session.commit()

        class MutableYearProvider:
            source_id = "scopus"
            region = "foreign"
            ingest_scope = "year"

            def __init__(self):
                self.papers = [
                    {"source_identifier": "a", "title": "A", "volume": "63", "issue": "1"},
                    {"source_identifier": "b", "title": "B", "volume": "63", "issue": "2"},
                ]

            def fetch_issue(self, journal_name, year, issue, **kwargs):
                return {
                    "issue": {
                        "source_type": "scopus",
                        "region": "foreign",
                        "journal_name": journal_name,
                        "year": year,
                        "issue": "year",
                    },
                    "papers": self.papers,
                }

        provider = MutableYearProvider()
        service = IngestionService(providers={"scopus": provider})
        _, initial = service.run_ingestion("scopus", journal.name, 2026, "year")
        first_id, second_id = initial[0].id, initial[1].id

        provider.papers = [
            {"source_identifier": "a2", "title": "A revised", "volume": "63", "issue": "1"},
            {"source_identifier": "b", "title": "B", "volume": "63", "issue": "2"},
        ]
        _, refreshed = service.run_ingestion(
            "scopus",
            journal.name,
            2026,
            "year",
            target_volume="63",
            target_issue="1",
        )

        self.assertEqual([item.id for item in refreshed], [first_id])
        self.assertEqual(refreshed[0].papers[0].title, "A revised")
        from app.collection.models import RawIssue

        untouched = db.session.get(RawIssue, second_id)
        self.assertEqual(untouched.papers[0].title, "B")

    def test_targeted_year_refresh_does_not_clear_issue_when_source_returns_no_match(self):
        from app.collection.sources.base import ProviderError
        from app.collection.services.ingestion_service import IngestionService
        from app.papers.models import Journal

        journal = Journal(name="IP&M", issn="0306-4573", region="foreign")
        db.session.add(journal)
        db.session.commit()

        class MutableYearProvider:
            source_id = "scopus"
            region = "foreign"
            ingest_scope = "year"
            papers = [{"source_identifier": "a", "title": "A", "volume": "63", "issue": "1"}]

            def fetch_issue(self, journal_name, year, issue, **kwargs):
                return {
                    "issue": {
                        "source_type": "scopus",
                        "region": "foreign",
                        "journal_name": journal_name,
                        "year": year,
                        "issue": "year",
                    },
                    "papers": self.papers,
                }

        provider = MutableYearProvider()
        service = IngestionService(providers={"scopus": provider})
        _, initial = service.run_ingestion("scopus", journal.name, 2026, "year")
        raw_issue = initial[0]
        provider.papers = []

        with self.assertRaises(ProviderError):
            service.run_ingestion(
                "scopus",
                journal.name,
                2026,
                "year",
                target_volume="63",
                target_issue="1",
            )

        db.session.refresh(raw_issue)
        self.assertEqual(raw_issue.paper_count, 1)
        self.assertEqual(raw_issue.papers[0].title, "A")


if __name__ == "__main__":
    unittest.main()
