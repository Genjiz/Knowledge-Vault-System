"""通过用户日常 Microsoft Edge 获取授权可访问的 ScienceDirect PDF。"""

import tempfile
from pathlib import Path

from app.collection.fulltext.base import (
    AccessBlockedError,
    AccessDeniedError,
    BrowserUnavailableError,
    FullTextProviderError,
    HumanVerificationRequired,
    NotPdfError,
    TooLargeError,
)
from app.collection.runtime.edge_desktop import (
    EdgeAccessBlocked,
    EdgeAccessDenied,
    EdgeAutomationError,
    EdgeDesktopGateway,
    EdgeDownloadTooLarge,
    EdgeUnavailableError,
    EdgeVerificationRequired,
)
from app.collection.sources.base import PdfDownload


ARTICLE_URL = "https://www.sciencedirect.com/science/article/pii/{pii}"
_DEFAULT_BROWSER_GATEWAY = EdgeDesktopGateway()


class ScienceDirectFullTextProvider:
    provider_id = "sciencedirect"

    def __init__(self, browser_gateway=None):
        self._browser_gateway = browser_gateway or _DEFAULT_BROWSER_GATEWAY

    def download_pdf(self, paper_ref, **kwargs):
        pii = str(paper_ref.get("pii") or "").strip()
        if not pii or not pii.isalnum():
            raise NotPdfError("缺少 ScienceDirect PII，无法定位 PDF")
        article_url = ARTICLE_URL.format(pii=pii)
        download_dir = Path(kwargs.get("download_dir") or tempfile.gettempdir())
        max_pdf_size = int(kwargs.get("max_pdf_size") or 100 * 1024 * 1024)
        try:
            content = self._browser_gateway.download_pdf(
                article_url=article_url,
                pii=pii,
                download_dir=download_dir,
                max_pdf_size=max_pdf_size,
            )
        except EdgeVerificationRequired as exc:
            raise HumanVerificationRequired(str(exc), action_url=article_url) from exc
        except EdgeAccessBlocked as exc:
            raise AccessBlockedError(str(exc), action_url=article_url) from exc
        except EdgeAccessDenied as exc:
            raise AccessDeniedError(str(exc), action_url=article_url) from exc
        except EdgeDownloadTooLarge as exc:
            raise TooLargeError(str(exc), action_url=article_url) from exc
        except EdgeUnavailableError as exc:
            raise BrowserUnavailableError(str(exc), action_url=article_url) from exc
        except EdgeAutomationError as exc:
            raise FullTextProviderError(str(exc), action_url=article_url) from exc
        return PdfDownload(
            content=content,
            source_url=article_url,
            content_type="application/pdf",
        )
