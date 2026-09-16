"""采集源能力声明与包导出的合同测试（T-1 阶段 0）。"""
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class SourceCapabilityDeclarationTestCase(unittest.TestCase):
    """每个源必须声明身份与能力，注册表与前端据此工作。"""

    def _assert_source_contract(
        self, cls, source_id, region, needs_browser, list_issues, ingest_scope="issue"
    ):
        self.assertEqual(cls.source_id, source_id)
        self.assertEqual(cls.region, region)
        self.assertTrue(cls.display_name)
        self.assertEqual(cls.capabilities["needs_browser"], needs_browser)
        self.assertEqual(cls.capabilities["list_issues"], list_issues)
        self.assertEqual(cls.ingest_scope, ingest_scope)
        self.assertIsInstance(cls.config_fields, list)

    def test_ncpssd_declares_capabilities(self):
        from app.collection.sources.ncpssd import NcpssdSource

        self._assert_source_contract(
            NcpssdSource, "ncpssd", "domestic", needs_browser=True, list_issues=False
        )

    def test_elsevier_declares_capabilities(self):
        from app.collection.sources.elsevier import ElsevierSource

        self._assert_source_contract(
            ElsevierSource, "elsevier", "foreign", needs_browser=True, list_issues=False
        )

    def test_magtech_declares_capabilities(self):
        from app.collection.sources.magtech import MagtechSource

        self._assert_source_contract(
            MagtechSource, "magtech", "domestic", needs_browser=False, list_issues=True
        )

    def test_scopus_declares_year_scope(self):
        from app.collection.sources.scopus import ScopusSource

        self._assert_source_contract(
            ScopusSource,
            "scopus",
            "foreign",
            needs_browser=False,
            list_issues=False,
            ingest_scope="year",
        )
        self.assertFalse(ScopusSource.capabilities["download_pdf"])

    def test_sources_package_exports_all_sources(self):
        import app.collection.sources as sources

        for name in (
            "SourceAdapter",
            "ProviderError",
            "NcpssdSource",
            "ElsevierSource",
            "MagtechSource",
            "ScopusSource",
        ):
            self.assertTrue(hasattr(sources, name), f"sources 包缺少导出：{name}")


class RawPaperDoiFieldTestCase(unittest.TestCase):
    """官网源可提供 DOI，raw_paper 需要承载该字段。"""

    def test_raw_paper_has_doi_column(self):
        from app.collection.models import RawPaper

        self.assertTrue(hasattr(RawPaper, "doi"))
        columns = {column.name for column in RawPaper.__table__.columns}
        self.assertIn("doi", columns)

    def test_raw_paper_to_dict_includes_doi(self):
        from app.collection.models import RawPaper

        paper = RawPaper(raw_issue_id=1, title="t", doi="10.0000/example")
        self.assertEqual(paper.to_dict()["doi"], "10.0000/example")

    def test_raw_paper_has_paper_level_volume_and_issue(self):
        from app.collection.models import RawPaper

        paper = RawPaper(raw_issue_id=1, title="t", volume="72", issue="2PA")
        self.assertEqual(paper.to_dict()["volume"], "72")
        self.assertEqual(paper.to_dict()["issue"], "2PA")


class LegacySourceTestConnectionTestCase(unittest.TestCase):
    """测试连接要取回可识别信息，让用户确认没配错源（计划 4.3）。

    网络预检用 patch 拦截，不发起真实请求。
    """

    def _ok_response(self):
        return mock.Mock(status_code=200)

    def test_ncpssd_reports_cached_journal(self):
        from app.collection.sources.ncpssd import NcpssdSource

        provider = NcpssdSource()
        with mock.patch.object(provider._session, "get", return_value=self._ok_response()):
            result = provider.test_connection(journal_name="情报学报")

        self.assertEqual(result["status"], "ok")
        self.assertIn("情报学报", result["message"])

    def test_ncpssd_warns_when_journal_not_cached(self):
        from app.collection.sources.ncpssd import NcpssdSource

        provider = NcpssdSource()
        with mock.patch.object(provider._session, "get", return_value=self._ok_response()):
            result = provider.test_connection(journal_name="某未收录期刊")

        self.assertEqual(result["status"], "warn")
        self.assertIn("未收录", result["message"])

    def test_ncpssd_reports_network_failure(self):
        from app.collection.sources.ncpssd import NcpssdSource

        provider = NcpssdSource()
        with mock.patch.object(
            provider._session, "get", side_effect=requests.RequestException("timeout")
        ):
            result = provider.test_connection(journal_name="情报学报")

        self.assertEqual(result["status"], "failed")

    def test_elsevier_reports_configured_slug(self):
        from app.collection.sources.elsevier import ElsevierSource

        with mock.patch("app.collection.sources.elsevier.requests") as fake_requests:
            fake_requests.get.return_value = self._ok_response()
            result = ElsevierSource().test_connection(journal_name="IP&M")

        self.assertEqual(result["status"], "ok")
        self.assertIn("IP&M", result["message"])

    def test_elsevier_warns_when_slug_missing(self):
        from app.collection.sources.elsevier import ElsevierSource

        with mock.patch("app.collection.sources.elsevier.requests") as fake_requests:
            fake_requests.get.return_value = self._ok_response()
            result = ElsevierSource().test_connection(journal_name="某未收录期刊")

        self.assertEqual(result["status"], "warn")
        self.assertIn("slug", result["message"])


if __name__ == "__main__":
    unittest.main()
