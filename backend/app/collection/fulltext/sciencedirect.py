"""通过 ScienceDirect 网页会话获取授权可访问的 PDF。"""

import re
import time

import requests

from app.collection.fulltext.base import (
    AccessBlockedError,
    AccessDeniedError,
    HumanVerificationRequired,
    NetworkError,
    NotPdfError,
    FullTextProviderError,
)
from app.collection.runtime.chromium import ChromiumSessionGateway
from app.collection.sources.base import PdfDownload


PDF_URL = (
    "https://www.sciencedirect.com/science/article/pii/{pii}/pdfft"
    "?isDTMRedir=true&download=true"
)
ARTICLE_URL = "https://www.sciencedirect.com/science/article/pii/{pii}"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}
_CHALLENGE_MARKERS = (
    b"verify you are human",
    b"just a moment",
    b"captcha",
    b"hcaptcha",
    b"recaptcha",
    b"challenge-platform",
    b"cf-chl-",
)
_BLOCKED_MARKERS = (
    b"cpe00001",
    b"cloudflare_error_1000s_box",
    b"there was a problem providing the content you requested",
)
_DENIED_MARKERS = (
    b"you do not have access",
    b"institutional access",
    b"purchase pdf",
    b"sign in to view",
)
_VALID_PII_RE = re.compile(r"^[A-Za-z0-9]+$")
_DEFAULT_BROWSER_GATEWAY = ChromiumSessionGateway()


class ScienceDirectFullTextProvider:
    provider_id = "sciencedirect"

    def __init__(
        self,
        session_factory=None,
        browser_gateway=None,
        sleep=None,
        monotonic=None,
        timeout=60,
        max_retries=3,
        min_interval=2.0,
    ):
        self._session_factory = session_factory or requests.Session
        self._browser_gateway = browser_gateway or _DEFAULT_BROWSER_GATEWAY
        self._sleep = sleep or time.sleep
        self._monotonic = monotonic or time.monotonic
        self._timeout = max(1, int(timeout))
        self._max_retries = max(1, int(max_retries))
        self._min_interval = max(0.0, float(min_interval))
        self._last_download_started_at = None

    def _pace(self):
        now = self._monotonic()
        if self._last_download_started_at is not None:
            remaining = self._min_interval - (now - self._last_download_started_at)
            if remaining > 0:
                self._sleep(remaining)
                now = self._monotonic()
        self._last_download_started_at = now

    def _session(self):
        session = self._session_factory()
        session.headers.update(DEFAULT_HEADERS)
        state = self._browser_gateway.session_state()
        if state.get("user_agent"):
            session.headers["User-Agent"] = state["user_agent"]
        for cookie in state.get("cookies") or []:
            kwargs = {
                key: cookie[key]
                for key in ("domain", "path", "secure", "expires")
                if cookie.get(key) not in (None, "")
            }
            session.cookies.set(cookie["name"], cookie.get("value") or "", **kwargs)
        return session

    @staticmethod
    def _classify(response, article_url):
        body = (response.content or b"").lower()
        if body.startswith(b"%pdf-"):
            return
        if any(marker in body for marker in _BLOCKED_MARKERS):
            raise AccessBlockedError(
                "ScienceDirect 拒绝了当前网络出口，请切换校园网或 aTrust/VPN 后继续",
                action_url=article_url,
            )
        if any(marker in body for marker in _CHALLENGE_MARKERS):
            raise HumanVerificationRequired(
                "ScienceDirect 要求人机验证，请在受控浏览器中手动完成后继续任务",
                action_url=article_url,
            )
        if response.status_code == 429:
            raise AccessBlockedError(
                "ScienceDirect 请求过于频繁，请稍后再继续任务",
                action_url=article_url,
            )
        if response.status_code in (401, 403) or any(
            marker in body for marker in _DENIED_MARKERS
        ):
            raise AccessDeniedError(
                "当前机构会话没有该论文的全文访问权限",
                action_url=article_url,
            )
        raise NotPdfError("ScienceDirect 返回内容不是 PDF", action_url=article_url)

    def download_pdf(self, paper_ref, **kwargs):
        pii = str(paper_ref.get("pii") or "").strip()
        if not pii or not _VALID_PII_RE.fullmatch(pii):
            raise NotPdfError("缺少 ScienceDirect PII，无法定位 PDF")
        article_url = ARTICLE_URL.format(pii=pii)
        pdf_url = PDF_URL.format(pii=pii)
        session = self._session()
        headers = {"Referer": article_url}
        self._pace()

        for attempt in range(self._max_retries):
            try:
                response = session.get(
                    pdf_url,
                    headers=headers,
                    timeout=self._timeout,
                    allow_redirects=True,
                )
            except requests.RequestException as exc:
                if attempt + 1 >= self._max_retries:
                    raise NetworkError(f"ScienceDirect 请求失败：{exc}") from exc
                self._sleep(2**attempt)
                continue

            if response.status_code >= 500 and attempt + 1 < self._max_retries:
                self._sleep(2**attempt)
                continue
            if response.status_code >= 500:
                raise FullTextProviderError(
                    f"ScienceDirect 服务暂不可用（HTTP {response.status_code}）",
                    action_url=article_url,
                )
            try:
                self._classify(response, article_url)
            except HumanVerificationRequired as exc:
                try:
                    self._browser_gateway.open_for_verification(article_url)
                except Exception as browser_error:
                    raise HumanVerificationRequired(
                        f"{exc}；受控浏览器启动失败，请检查浏览器路径配置",
                        action_url=article_url,
                    ) from browser_error
                raise
            return PdfDownload(
                content=response.content,
                source_url=response.url or pdf_url,
                content_type=response.headers.get("Content-Type"),
            )

        raise NetworkError("ScienceDirect 请求重试次数已耗尽")
