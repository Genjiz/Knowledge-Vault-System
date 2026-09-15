import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeResponse:
    def __init__(self, content, status_code=200, content_type="application/pdf", url=None):
        self.content = content
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}
        self.url = url or "https://www.sciencedirect.com/science/article/pii/TEST/pdfft"


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.cookies = type("Cookies", (), {"set": lambda self, *args, **kwargs: None})()
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class FakeBrowserGateway:
    def __init__(self):
        self.opened = []

    def session_state(self):
        return {"user_agent": "Edge test agent", "cookies": []}

    def open_for_verification(self, url):
        self.opened.append(url)


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

    def test_valid_pdf_is_returned_without_browser_interaction(self):
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        session = FakeSession([FakeResponse(b"%PDF-1.7\nfixture")])
        browser = FakeBrowserGateway()
        provider = ScienceDirectFullTextProvider(
            session_factory=lambda: session,
            browser_gateway=browser,
            max_retries=1,
        )

        result = provider.download_pdf({"pii": "S0306457326003201"})

        self.assertTrue(result.content.startswith(b"%PDF-"))
        self.assertEqual(browser.opened, [])
        self.assertIn("/S0306457326003201/pdfft", session.calls[0][0])

    def test_human_challenge_opens_controlled_browser_and_pauses(self):
        from app.collection.fulltext.base import HumanVerificationRequired
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        response = FakeResponse(
            b"<html><title>Just a moment...</title>Verify you are human</html>",
            status_code=403,
            content_type="text/html; charset=UTF-8",
        )
        session = FakeSession([response])
        browser = FakeBrowserGateway()
        provider = ScienceDirectFullTextProvider(
            session_factory=lambda: session,
            browser_gateway=browser,
            max_retries=1,
        )

        with self.assertRaises(HumanVerificationRequired) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "verification_required")
        self.assertEqual(browser.opened, [captured.exception.action_url])

    def test_cloudflare_cpe_error_is_access_blocked_not_captcha(self):
        from app.collection.fulltext.base import AccessBlockedError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        response = FakeResponse(
            b"<html>There was a problem providing the content CPE00001 "
            b"::CLOUDFLARE_ERROR_1000S_BOX::</html>",
            status_code=403,
            content_type="text/html; charset=UTF-8",
        )
        session = FakeSession([response])
        browser = FakeBrowserGateway()
        provider = ScienceDirectFullTextProvider(
            session_factory=lambda: session,
            browser_gateway=browser,
            max_retries=1,
        )

        with self.assertRaises(AccessBlockedError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "access_blocked")
        self.assertEqual(browser.opened, [])

    def test_subscription_denial_does_not_open_verification_browser(self):
        from app.collection.fulltext.base import AccessDeniedError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        response = FakeResponse(
            b"<html>You do not have access to this article. Purchase PDF.</html>",
            status_code=403,
            content_type="text/html; charset=UTF-8",
        )
        session = FakeSession([response])
        browser = FakeBrowserGateway()
        provider = ScienceDirectFullTextProvider(
            session_factory=lambda: session,
            browser_gateway=browser,
            max_retries=1,
        )

        with self.assertRaises(AccessDeniedError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "access_denied")
        self.assertEqual(browser.opened, [])

    def test_server_error_retries_then_reports_remote_error(self):
        from app.collection.fulltext.base import FullTextProviderError
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        session = FakeSession(
            [
                FakeResponse(b"temporary", status_code=503, content_type="text/html"),
                FakeResponse(b"still unavailable", status_code=503, content_type="text/html"),
            ]
        )
        delays = []
        provider = ScienceDirectFullTextProvider(
            session_factory=lambda: session,
            browser_gateway=FakeBrowserGateway(),
            sleep=delays.append,
            max_retries=2,
        )

        with self.assertRaises(FullTextProviderError) as captured:
            provider.download_pdf({"pii": "S0306457326003201"})

        self.assertEqual(captured.exception.code, "remote_error")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(delays, [1])

    def test_controlled_browser_gateway_keeps_session_in_memory(self):
        from app.collection.runtime.chromium import ChromiumSessionGateway

        class Page:
            url = "about:blank"
            user_agent = "Edge test agent"

            def __init__(self):
                self.opened = []

            def get(self, url):
                self.url = url
                self.opened.append(url)

            def cookies(self, all_domains=False, all_info=False):
                return [{"name": "session", "value": "test", "domain": ".example.com"}]

        page = Page()
        gateway = ChromiumSessionGateway(page_factory=lambda: page)

        gateway.open_for_verification("https://example.com/challenge")
        state = gateway.session_state()

        self.assertEqual(page.opened, ["https://example.com/challenge"])
        self.assertEqual(state["user_agent"], "Edge test agent")
        self.assertEqual(state["cookies"][0]["name"], "session")


if __name__ == "__main__":
    unittest.main()
