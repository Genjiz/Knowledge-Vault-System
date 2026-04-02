import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class DomesticProviderContractTestCase(unittest.TestCase):
    def test_domestic_provider_returns_structured_issue_payload(self):
        from app.crawler.providers.domestic_provider import DomesticCrawlerProvider

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

        provider = DomesticCrawlerProvider(crawler_factory=FakeCrawler)
        payload = provider.fetch_issue("图书情报知识", 2024, 6)

        self.assertEqual(payload["issue"]["source_type"], "domestic")
        self.assertEqual(payload["issue"]["journal_name"], "图书情报知识")
        self.assertEqual(payload["issue"]["issue"], "6")
        self.assertEqual(payload["issue"]["source_url"], "https://example.com/issue")
        self.assertEqual(payload["papers"][0]["title"], "Paper A")
        self.assertEqual(payload["papers"][0]["keywords_json"], '["k1", "k2"]')

    def test_domestic_provider_tolerates_legacy_console_output(self):
        from app.crawler.providers.domestic_provider import DomesticCrawlerProvider

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

        provider = DomesticCrawlerProvider(crawler_factory=FakeCrawler)
        payload = provider.fetch_issue("\u6d4b\u8bd5\u671f\u520a", 2024, "3")

        self.assertEqual(payload["papers"][0]["title"], "Paper A")

    def test_domestic_provider_precheck_error_message_is_clear(self):
        from app.crawler.providers.base import ProviderError
        from app.crawler.providers.domestic_provider import DomesticCrawlerProvider
        import requests
        from unittest.mock import patch

        provider = DomesticCrawlerProvider(crawler_factory=lambda: None, enable_network_precheck=True)

        with patch(
            "app.crawler.providers.domestic_provider.requests.get",
            side_effect=requests.RequestException("network down"),
        ):
            with self.assertRaises(ProviderError) as ctx:
                provider.fetch_issue("测试期刊", 2024, "3")

        message = str(ctx.exception)
        self.assertIn("Domestic network precheck failed", message)
        self.assertIn("关闭 VPN", message)


if __name__ == "__main__":
    unittest.main()
