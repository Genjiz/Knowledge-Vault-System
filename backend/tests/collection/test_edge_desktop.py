import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeEdgeAdapter:
    def __init__(
        self,
        payload=b"%PDF-1.7\nfixture\n%%EOF",
        viewer_results=None,
        available_error=None,
    ):
        self.payload = payload
        self.viewer_results = list(viewer_results or [
            "https://pdf.sciencedirectassets.com/main.pdf?pii=S0306457326004826"
        ])
        self.available_error = available_error
        self.calls = []

    def initialize_thread(self):
        self.calls.append(("initialize_thread",))
        return "com-token"

    def uninitialize_thread(self, token):
        self.calls.append(("uninitialize_thread", token))

    def open_article(self, article_url):
        self.calls.append(("open_article", article_url))
        return object()

    def wait_until_download_available(self, session, pii):
        self.calls.append(("wait_until_download_available", pii))
        if self.available_error:
            raise self.available_error

    def click_view_pdf(self, session, pii):
        self.calls.append(("click_view_pdf", pii))

    def wait_for_pdf_viewer(self, session, pii):
        self.calls.append(("wait_for_pdf_viewer", pii))
        result = self.viewer_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def refresh_article(self, session):
        self.calls.append(("refresh_article",))

    def save_pdf(self, session, destination):
        self.calls.append(("save_pdf", destination))
        destination.write_bytes(self.payload)

    def finish(self, session, preserve_article=False):
        self.calls.append(("finish", preserve_article))


class EdgeDesktopGatewayTestCase(unittest.TestCase):
    def test_visible_browser_flow_returns_pdf_and_removes_temporary_file(self):
        from app.collection.runtime.edge_desktop import EdgeDesktopGateway

        adapter = FakeEdgeAdapter()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = EdgeDesktopGateway(adapter=adapter).download_pdf(
                article_url=(
                    "https://www.sciencedirect.com/science/article/pii/"
                    "S0306457326004826"
                ),
                pii="S0306457326004826",
                download_dir=Path(temp_dir),
                max_pdf_size=1024,
            )

            self.assertEqual(result, adapter.payload)
            self.assertEqual(list(Path(temp_dir).glob(".edge-download-*.pdf")), [])
        self.assertIn(("click_view_pdf", "S0306457326004826"), adapter.calls)
        self.assertEqual(adapter.calls[0], ("initialize_thread",))
        self.assertIn(("finish", False), adapter.calls)
        self.assertEqual(adapter.calls[-1], ("uninitialize_thread", "com-token"))

    def test_internal_error_refreshes_article_once_before_retrying(self):
        from app.collection.runtime.edge_desktop import (
            EdgeDesktopGateway,
            EdgeInternalServerError,
        )

        adapter = FakeEdgeAdapter(
            viewer_results=[
                EdgeInternalServerError("Internal Server Error"),
                "https://pdf.sciencedirectassets.com/main.pdf?pii=S0306457326004826",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            EdgeDesktopGateway(adapter=adapter).download_pdf(
                article_url=(
                    "https://www.sciencedirect.com/science/article/pii/"
                    "S0306457326004826"
                ),
                pii="S0306457326004826",
                download_dir=Path(temp_dir),
            )

        self.assertEqual(adapter.calls.count(("click_view_pdf", "S0306457326004826")), 2)
        self.assertEqual(adapter.calls.count(("refresh_article",)), 1)

    def test_verification_keeps_article_open_for_user(self):
        from app.collection.runtime.edge_desktop import (
            EdgeDesktopGateway,
            EdgeVerificationRequired,
        )

        adapter = FakeEdgeAdapter(
            available_error=EdgeVerificationRequired("需要完成人机验证")
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(EdgeVerificationRequired):
                EdgeDesktopGateway(adapter=adapter).download_pdf(
                    article_url=(
                        "https://www.sciencedirect.com/science/article/pii/"
                        "S0306457326004826"
                    ),
                    pii="S0306457326004826",
                    download_dir=Path(temp_dir),
                )

        self.assertIn(("finish", True), adapter.calls)
        self.assertEqual(adapter.calls[-1], ("uninitialize_thread", "com-token"))

    def test_wrong_pii_in_pdf_viewer_is_rejected_before_save(self):
        from app.collection.runtime.edge_desktop import (
            EdgeAutomationError,
            EdgeDesktopGateway,
        )

        adapter = FakeEdgeAdapter(
            viewer_results=[
                "https://pdf.sciencedirectassets.com/main.pdf?pii=S0000000000000000"
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(EdgeAutomationError):
                EdgeDesktopGateway(adapter=adapter).download_pdf(
                    article_url=(
                        "https://www.sciencedirect.com/science/article/pii/"
                        "S0306457326004826"
                    ),
                    pii="S0306457326004826",
                    download_dir=Path(temp_dir),
                )

        self.assertFalse(any(call[0] == "save_pdf" for call in adapter.calls))
        self.assertIn(("finish", False), adapter.calls)

    def test_oversized_browser_download_is_rejected(self):
        from app.collection.runtime.edge_desktop import (
            EdgeDesktopGateway,
            EdgeDownloadTooLarge,
        )

        adapter = FakeEdgeAdapter(payload=b"%PDF-" + b"x" * 32)
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(EdgeDownloadTooLarge):
                EdgeDesktopGateway(adapter=adapter).download_pdf(
                    article_url=(
                        "https://www.sciencedirect.com/science/article/pii/"
                        "S0306457326004826"
                    ),
                    pii="S0306457326004826",
                    download_dir=Path(temp_dir),
                    max_pdf_size=16,
                )

    def test_browser_download_without_pdf_eof_is_rejected(self):
        from app.collection.runtime.edge_desktop import (
            EdgeAutomationError,
            EdgeDesktopGateway,
        )

        adapter = FakeEdgeAdapter(payload=b"%PDF-1.7\npartial")
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(EdgeAutomationError):
                EdgeDesktopGateway(adapter=adapter).download_pdf(
                    article_url=(
                        "https://www.sciencedirect.com/science/article/pii/"
                        "S0306457326004826"
                    ),
                    pii="S0306457326004826",
                    download_dir=Path(temp_dir),
                )


if __name__ == "__main__":
    unittest.main()
