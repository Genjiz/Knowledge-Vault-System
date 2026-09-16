import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class DomesticProviderContractTestCase(unittest.TestCase):
    def test_default_session_is_direct_and_passed_to_crawler(self):
        from app.collection.sources.ncpssd import NcpssdSource

        class FakeCrawler:
            received_session = None

            def __init__(self, session=None):
                type(self).received_session = session

            def crawl_journal_papers(self, journal_name, year, issue):
                return {
                    "success": True,
                    "journal_name": journal_name,
                    "year": year,
                    "issue": issue,
                    "papers": [],
                }

        provider = NcpssdSource(crawler_factory=FakeCrawler)
        provider.fetch_issue("测试期刊", 2024, 3)

        self.assertFalse(provider._session.trust_env)
        self.assertIs(FakeCrawler.received_session, provider._session)

    def test_domestic_provider_returns_structured_issue_payload(self):
        from app.collection.sources.ncpssd import NcpssdSource

        class FakeCrawler:
            def crawl_journal_papers(self, journal_name, year, issue):
                return {
                    "success": True,
                    "journal_name": journal_name,
                    "year": year,
                    "issue": issue,
                    "issue_url": "https://example.com/issue",
                    "papers": [
                        {
                            "title": "Paper A",
                            "authors": "Author One",
                            "abstract": "Abstract A",
                            "keywords": ["k1", "k2"],
                            "detail_url": "https://example.com/a",
                        }
                    ],
                }

        provider = NcpssdSource(crawler_factory=FakeCrawler)
        payload = provider.fetch_issue("图书情报知识", 2024, 6)

        self.assertEqual(payload["issue"]["source_type"], "ncpssd")
        self.assertEqual(payload["issue"]["region"], "domestic")
        self.assertEqual(payload["issue"]["journal_name"], "图书情报知识")
        self.assertEqual(payload["issue"]["issue"], "6")
        self.assertEqual(payload["issue"]["source_url"], "https://example.com/issue")
        self.assertEqual(payload["papers"][0]["title"], "Paper A")
        self.assertEqual(payload["papers"][0]["keywords_json"], '["k1", "k2"]')

    def test_domestic_provider_tolerates_legacy_console_output(self):
        from app.collection.sources.ncpssd import NcpssdSource

        class FakeCrawler:
            def crawl_journal_papers(self, journal_name, year, issue):
                print("legacy output \U0001f680")
                return {
                    "success": True,
                    "journal_name": journal_name,
                    "year": year,
                    "issue": issue,
                    "papers": [{"title": "Paper A", "keywords": []}],
                }

        provider = NcpssdSource(crawler_factory=FakeCrawler)
        payload = provider.fetch_issue("\u6d4b\u8bd5\u671f\u520a", 2024, "3")

        self.assertEqual(payload["papers"][0]["title"], "Paper A")

    def test_domestic_provider_precheck_error_message_is_clear(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.ncpssd import NcpssdSource
        import requests
        from unittest.mock import patch

        provider = NcpssdSource(crawler_factory=lambda: None, enable_network_precheck=True)

        with patch.object(
            provider._session, "get", side_effect=requests.RequestException("network down")
        ):
            with self.assertRaises(ProviderError) as ctx:
                provider.fetch_issue("测试期刊", 2024, "3")

        message = str(ctx.exception)
        self.assertIn("Domestic network precheck failed", message)
        self.assertIn("关闭 VPN", message)


if __name__ == "__main__":
    unittest.main()
