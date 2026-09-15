import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeBrowserGateway:
    def __init__(self, payload=b"%PDF-1.7\nfixture"):
        self.payload = payload
        self.calls = []

    def download_pdf(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class ScienceDirectFullTextTestCase(unittest.TestCase):
    def test_reference_uses_scopus_pii(self):
        from app.collection.fulltext.registry import resolve_fulltext_reference

        class Issue:
            source_type = "scopus"

        class Paper:
            raw_issue = Issue()
            source_ref_json = '{"pii":"S0306457326003201"}'
            detail_url = "https://www.sciencedirect.com/science/article/pii/S0306457326003201"
            doi = "10.1016/j.ipm.2026.104929"

        reference = resolve_fulltext_reference(Paper())

        self.assertEqual(reference.provider_id, "sciencedirect")
        self.assertEqual(reference.paper_ref["pii"], "S0306457326003201")

    def test_reference_normalizes_legacy_scopus_pii(self):
        from app.collection.fulltext.registry import resolve_fulltext_reference

        class Issue:
            source_type = "scopus"

        class Paper:
            raw_issue = Issue()
            source_ref_json = '{"pii":"S0306-4573(25)00349-8"}'
            detail_url = "https://www.sciencedirect.com/science/article/pii/S0306-4573(25)00349-8"
            doi = "10.1016/j.ipm.2025.104408"

        reference = resolve_fulltext_reference(Paper())

        self.assertEqual(reference.provider_id, "sciencedirect")
        self.assertEqual(reference.paper_ref["pii"], "S0306457325003498")
        self.assertEqual(
            reference.action_url,
            "https://www.sciencedirect.com/science/article/pii/S0306457325003498",
        )

    def test_reference_rejects_unrecognized_pii_punctuation(self):
        from app.collection.fulltext.registry import resolve_fulltext_reference

        class Issue:
            source_type = "scopus"

        class Paper:
            raw_issue = Issue()
            source_ref_json = '{"pii":"S0306/4573(25)00349-8"}'
            detail_url = ""
            doi = "10.1016/j.ipm.2025.104408"

        self.assertIsNone(resolve_fulltext_reference(Paper()))

    def test_valid_pdf_is_downloaded_through_ordinary_edge(self):
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        browser = FakeBrowserGateway()
        provider = ScienceDirectFullTextProvider(browser_gateway=browser)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = provider.download_pdf(
                {"pii": "S0306457326003201"},
                download_dir=Path(temp_dir),
                max_pdf_size=2048,
            )

        self.assertTrue(result.content.startswith(b"%PDF-"))
        self.assertEqual(
            result.source_url,
            "https://www.sciencedirect.com/science/article/pii/S0306457326003201",
        )
        self.assertEqual(browser.calls[0]["pii"], "S0306457326003201")
        self.assertEqual(browser.calls[0]["max_pdf_size"], 2048)

    def test_human_challenge_from_edge_pauses_task(self):
        from app.collection.fulltext.base import HumanVerificationRequired
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider
        from app.collection.runtime.edge_desktop import EdgeVerificationRequired

        browser = FakeBrowserGateway(
            EdgeVerificationRequired("ScienceDirect 要求人机验证")
        )
        provider = ScienceDirectFullTextProvider(browser_gateway=browser)

        with self.assertRaises(HumanVerificationRequired) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "verification_required")
        self.assertIn("S0306457326003201", captured.exception.action_url)

    def test_edge_navigation_block_is_access_blocked(self):
        from app.collection.fulltext.base import AccessBlockedError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider
        from app.collection.runtime.edge_desktop import EdgeAccessBlocked

        browser = FakeBrowserGateway(EdgeAccessBlocked("访问被阻止"))
        provider = ScienceDirectFullTextProvider(browser_gateway=browser)

        with self.assertRaises(AccessBlockedError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "access_blocked")

    def test_subscription_denial_from_edge_is_access_denied(self):
        from app.collection.fulltext.base import AccessDeniedError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider
        from app.collection.runtime.edge_desktop import EdgeAccessDenied

        browser = FakeBrowserGateway(EdgeAccessDenied("没有全文访问权限"))
        provider = ScienceDirectFullTextProvider(browser_gateway=browser)

        with self.assertRaises(AccessDeniedError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "access_denied")

    def test_browser_automation_error_is_remote_error(self):
        from app.collection.fulltext.base import FullTextProviderError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider
        from app.collection.runtime.edge_desktop import EdgeAutomationError

        provider = ScienceDirectFullTextProvider(
            browser_gateway=FakeBrowserGateway(EdgeAutomationError("Edge 控件超时"))
        )

        with self.assertRaises(FullTextProviderError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "remote_error")

    def test_edge_unavailable_pauses_for_environment_recovery(self):
        from app.collection.fulltext.base import BrowserUnavailableError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider
        from app.collection.runtime.edge_desktop import EdgeUnavailableError

        provider = ScienceDirectFullTextProvider(
            browser_gateway=FakeBrowserGateway(
                EdgeUnavailableError("后端进程无法访问 Windows 交互式桌面")
            )
        )

        with self.assertRaises(BrowserUnavailableError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "browser_unavailable")
        self.assertTrue(captured.exception.requires_user_action)
        self.assertIn("S0306457326003201", captured.exception.action_url)


if __name__ == "__main__":
    unittest.main()
