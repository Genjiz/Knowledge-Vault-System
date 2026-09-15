"""采集源注册表与采集身份统一测试（T-1 阶段 2，方案 A）。

- source_id 是唯一采集身份（ncpssd / magtech / elsevier / scopus）
- region 承担区域语义（domestic / foreign），供语言推断与前端分组
"""
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class SourceRegistryTestCase(unittest.TestCase):
    def test_describe_sources_lists_all_sources(self):
        from app.collection.sources.registry import describe_sources

        sources = describe_sources()
        by_id = {item["source_id"]: item for item in sources}

        self.assertEqual(set(by_id), {"ncpssd", "magtech", "elsevier", "scopus"})
        self.assertEqual(by_id["magtech"]["display_name"], "期刊官网（Magtech）")
        self.assertEqual(by_id["ncpssd"]["region"], "domestic")
        self.assertEqual(by_id["elsevier"]["region"], "foreign")
        self.assertTrue(by_id["magtech"]["capabilities"]["list_issues"])
        self.assertEqual(by_id["scopus"]["ingest_scope"], "year")
        self.assertEqual(by_id["elsevier"]["ingest_scope"], "issue")
        self.assertEqual(
            [field["key"] for field in by_id["magtech"]["config_fields"]], ["base_url"]
        )

    def test_get_source_builds_magtech_with_config(self):
        from app.collection.sources.magtech import MagtechSource
        from app.collection.sources.registry import get_source

        source = get_source("magtech", {"base_url": "https://qbxb.istic.ac.cn"})

        self.assertIsInstance(source, MagtechSource)
        self.assertEqual(source.base_url, "https://qbxb.istic.ac.cn")

    def test_get_source_magtech_without_base_url_raises(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.registry import get_source

        with self.assertRaises((ValueError, ProviderError)):
            get_source("magtech", {})

    def test_get_source_builds_legacy_sources_without_config(self):
        from app.collection.sources.ncpssd import NcpssdSource
        from app.collection.sources.elsevier import ElsevierSource
        from app.collection.sources.registry import get_source

        self.assertIsInstance(get_source("ncpssd"), NcpssdSource)
        self.assertIsInstance(get_source("elsevier", None), ElsevierSource)

    def test_get_source_builds_scopus_without_journal_config(self):
        from app.collection.sources.scopus import ScopusSource
        from app.collection.sources.registry import get_source

        self.assertIsInstance(get_source("scopus", None), ScopusSource)

    def test_get_source_unknown_id_raises_value_error(self):
        from app.collection.sources.registry import get_source

        with self.assertRaises(ValueError):
            get_source("domestic")

    def test_config_keys_are_passed_by_declared_fields_only(self):
        """注册表按源声明的 config_fields 传参，未声明字段不透传。"""
        from app.collection.sources.registry import get_source

        source = get_source(
            "magtech", {"base_url": "https://example.com", "unknown_key": "x"}
        )

        self.assertEqual(source.base_url, "https://example.com")


class SourceIdentityPayloadTestCase(unittest.TestCase):
    """源的返回身份必须是真实 source_id，区域放 region 字段。"""

    def test_ncpssd_payload_identity(self):
        from app.collection.sources.ncpssd import NcpssdSource

        class FakeCrawler:
            def crawl_journal_papers(self, journal_name, year, issue):
                return {
                    "success": True,
                    "journal_name": journal_name,
                    "year": year,
                    "issue": issue,
                    "papers": [{"title": "A", "keywords": []}],
                }

        payload = NcpssdSource(crawler_factory=FakeCrawler).fetch_issue("情报学报", 2026, 3)

        self.assertEqual(payload["issue"]["source_type"], "ncpssd")
        self.assertEqual(payload["issue"]["region"], "domestic")

    def test_elsevier_payload_identity(self):
        from app.collection.sources.elsevier import ElsevierSource

        class FakeMapper:
            def get_calculated_volume(self, journal_name, year):
                return "66"

        class FakeCrawler:
            def crawl_issue(self, source_url):
                return [{"title": "A", "keywords_json": "[]"}]

        source = ElsevierSource(
            mapper_factory=FakeMapper,
            crawler_factory=FakeCrawler,
            journal_slugs={"IP&M": "ipm"},
            base_url="https://example.com",
            enable_network_precheck=False,
        )
        payload = source.fetch_issue("IP&M", 2026, 6)

        self.assertEqual(payload["issue"]["source_type"], "elsevier")
        self.assertEqual(payload["issue"]["region"], "foreign")


class PaperMergeLanguageTestCase(unittest.TestCase):
    """语言推断改用 region：domestic → zh，foreign → en。"""

    def _make_raw_paper(self, region, source_type):
        from app.collection.models import RawIssue, RawPaper
        from app.collection.pipeline.paper_merge import PaperMergeService

        issue = RawIssue(
            source_type=source_type, journal_name="J", year=2026, issue="1", region=region
        )
        paper = RawPaper(raw_issue_id=1, title="T", authors="A")
        paper.raw_issue = issue

        captured = {}

        class FakeService:
            def upsert_literature(self, data):
                captured.update(data)
                return data

        PaperMergeService(paper_service=FakeService()).upsert_raw_paper(paper)
        return captured["language"]

    def test_domestic_region_maps_to_chinese(self):
        self.assertEqual(self._make_raw_paper("domestic", "ncpssd"), "zh")

    def test_foreign_region_maps_to_english(self):
        self.assertEqual(self._make_raw_paper("foreign", "elsevier"), "en")
        self.assertEqual(self._make_raw_paper("foreign", "scopus"), "en")

    def test_legacy_row_without_region_falls_back_to_source_id(self):
        self.assertEqual(self._make_raw_paper(None, "ncpssd"), "zh")
        self.assertEqual(self._make_raw_paper(None, "elsevier"), "en")


class SourceConfigColumnsTestCase(unittest.TestCase):
    """journal_source_config 支撑测试连接与默认源的新字段。"""

    def test_journal_source_config_has_new_columns(self):
        from app.papers.models import JournalSourceConfig

        columns = {column.name for column in JournalSourceConfig.__table__.columns}
        for name in ("is_default", "last_checked_at", "last_check_status", "last_check_message"):
            self.assertIn(name, columns)

    def test_task_and_issue_have_region_column(self):
        from app.collection.models import CrawlTask, RawIssue

        self.assertIn("region", {c.name for c in CrawlTask.__table__.columns})
        self.assertIn("region", {c.name for c in RawIssue.__table__.columns})


if __name__ == "__main__":
    unittest.main()
