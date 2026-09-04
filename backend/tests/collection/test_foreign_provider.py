import sys
import tempfile
import tempfile
import unittest
from pathlib import Path
import os
import shutil

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class ForeignProviderContractTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_profile_root = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "foreign-provider-profile"
        if self.temp_profile_root.exists():
            shutil.rmtree(self.temp_profile_root)
        self.temp_profile_root.mkdir(parents=True, exist_ok=True)
        self.original_browser_data_root = os.environ.get("CRAWLER_BROWSER_DATA_ROOT")
        os.environ["CRAWLER_BROWSER_DATA_ROOT"] = str(self.temp_profile_root)

    def tearDown(self):
        if self.original_browser_data_root is None:
            os.environ.pop("CRAWLER_BROWSER_DATA_ROOT", None)
        else:
            os.environ["CRAWLER_BROWSER_DATA_ROOT"] = self.original_browser_data_root
        if self.temp_profile_root.exists():
            shutil.rmtree(self.temp_profile_root)

    def test_foreign_provider_returns_structured_issue_payload(self):
        from app.collection.sources.elsevier import ElsevierSource

        class FakeMapper:
            def get_calculated_volume(self, journal_name, year):
                return 60

        class FakeCrawler:
            def crawl_issue(self, issue_url):
                self.last_issue_url = issue_url
                return [
                    {
                        "title": "Paper A",
                        "authors": "Author One",
                        "abstract": "Abstract A",
                        "detail_url": "https://example.com/a",
                    }
                ]

        provider = ElsevierSource(
            mapper_factory=FakeMapper,
            crawler_factory=FakeCrawler,
            journal_slugs={"Information Processing & Management": "information-processing-and-management"},
            base_url="https://example.com",
        )

        payload = provider.fetch_issue("Information Processing & Management", 2024, "6")

        self.assertEqual(payload["issue"]["source_type"], "elsevier")
        self.assertEqual(payload["issue"]["region"], "foreign")
        self.assertEqual(payload["issue"]["volume"], "60")
        self.assertEqual(payload["issue"]["issue"], "6")
        self.assertEqual(
            payload["issue"]["source_url"],
            "https://example.com/journal/information-processing-and-management/vol/60/issue/6",
        )
        self.assertEqual(payload["papers"][0]["title_zh"], "")
        self.assertEqual(payload["papers"][0]["abstract_zh"], "")

    def test_foreign_provider_raises_clear_error_for_unknown_journal(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.elsevier import ElsevierSource

        provider = ElsevierSource(
            mapper_factory=lambda: None,
            crawler_factory=lambda: None,
            journal_slugs={},
            base_url="https://example.com",
        )

        with self.assertRaises(ProviderError) as ctx:
            provider.fetch_issue("Unknown Journal", 2024, "6")

        self.assertIn("Unknown journal", str(ctx.exception))

    def test_foreign_provider_raises_when_crawler_returns_no_papers(self):
        from app.collection.sources.base import ProviderError
        from app.collection.sources.elsevier import ElsevierSource

        class FakeMapper:
            def get_calculated_volume(self, journal_name, year):
                return 60

        class FakeCrawler:
            def crawl_issue(self, issue_url):
                return []

        provider = ElsevierSource(
            mapper_factory=FakeMapper,
            crawler_factory=FakeCrawler,
            journal_slugs={"Information Processing & Management": "information-processing-and-management"},
            base_url="https://example.com",
        )

        with self.assertRaises(ProviderError) as ctx:
            provider.fetch_issue("Information Processing & Management", 2024, "6")

        self.assertIn("returned zero papers", str(ctx.exception))

    def test_foreign_provider_tolerates_legacy_console_output(self):
        from app.collection.sources.elsevier import ElsevierSource

        class FakeMapper:
            def get_calculated_volume(self, journal_name, year):
                return 60

        class FakeCrawler:
            def crawl_issue(self, issue_url):
                print("legacy output \U0001f680")
                return [{"title": "Paper A", "detail_url": "https://example.com/a"}]

        provider = ElsevierSource(
            mapper_factory=FakeMapper,
            crawler_factory=FakeCrawler,
            journal_slugs={"Information Processing & Management": "information-processing-and-management"},
            base_url="https://example.com",
        )

        payload = provider.fetch_issue("Information Processing & Management", 2024, "6")

        self.assertEqual(payload["papers"][0]["title"], "Paper A")

    def test_foreign_provider_precheck_error_message_is_clear(self):
        import requests
        from unittest.mock import patch
        from app.collection.sources.base import ProviderError
        from app.collection.sources.elsevier import ElsevierSource

        class FakeMapper:
            def get_calculated_volume(self, journal_name, year):
                return 60

        class FakeCrawler:
            def crawl_issue(self, issue_url):
                return [{"title": "Paper A"}]

        provider = ElsevierSource(
            mapper_factory=FakeMapper,
            crawler_factory=FakeCrawler,
            journal_slugs={"Information Processing & Management": "information-processing-and-management"},
            base_url="https://example.com",
            enable_network_precheck=True,
        )

        with patch(
            "app.collection.sources.elsevier.requests.get",
            side_effect=requests.RequestException("network down"),
        ):
            with self.assertRaises(ProviderError) as ctx:
                provider.fetch_issue("Information Processing & Management", 2024, "6")

        message = str(ctx.exception)
        self.assertIn("Foreign network precheck failed", message)
        self.assertIn("开启 VPN", message)

    def test_create_chromium_page_falls_back_from_attach_to_launch(self):
        from app.collection.sources.elsevier import ElsevierSource

        class FakeOptions:
            def __init__(self):
                self.local_port = None
                self.only_existing = False
                self.user_data_path = None
                self.browser_path = None

            def set_local_port(self, port):
                self.local_port = port

            def existing_only(self, flag):
                self.only_existing = bool(flag)

            def set_user_data_path(self, path):
                self.user_data_path = path

            def set_browser_path(self, path):
                self.browser_path = path

        class FakeModule:
            ChromiumOptions = FakeOptions
            calls = []

            @staticmethod
            def ChromiumPage(options):
                FakeModule.calls.append(options)
                if getattr(options, "only_existing", False):
                    raise RuntimeError("attach failed")
                return {"ok": True, "options": options}

        provider = ElsevierSource()
        provider._is_debug_port_open = lambda port: True
        page = provider._create_chromium_page(FakeModule, None, self.temp_profile_root)

        self.assertEqual(page["ok"], True)
        self.assertEqual(len(FakeModule.calls), 2)
        self.assertTrue(FakeModule.calls[0].only_existing)
        self.assertEqual(FakeModule.calls[1].user_data_path, str(self.temp_profile_root))

    def test_create_chromium_page_skips_attach_when_debug_port_is_closed(self):
        from app.collection.sources.elsevier import ElsevierSource

        class FakeOptions:
            def __init__(self):
                self.only_existing = False
                self.user_data_path = None

            def set_local_port(self, port):
                self.local_port = port

            def existing_only(self, flag):
                self.only_existing = bool(flag)

            def set_user_data_path(self, path):
                self.user_data_path = path

            def set_browser_path(self, path):
                self.browser_path = path

        class FakeModule:
            ChromiumOptions = FakeOptions
            calls = []

            @staticmethod
            def ChromiumPage(options):
                FakeModule.calls.append(options)
                return {"ok": True, "options": options}

        provider = ElsevierSource()
        provider._is_debug_port_open = lambda port: False
        page = provider._create_chromium_page(FakeModule, None, self.temp_profile_root)

        self.assertEqual(page["ok"], True)
        self.assertEqual(len(FakeModule.calls), 1)
        self.assertFalse(FakeModule.calls[0].only_existing)


if __name__ == "__main__":
    unittest.main()
