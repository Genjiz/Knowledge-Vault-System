"""通过普通 Microsoft Edge 和 Windows UI Automation 下载授权 PDF。"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from app.collection.runtime.paths import find_edge_executable


_VIEW_PDF_NAME = "View PDF. Opens in a new window."
_PDF_HOST = "pdf.sciencedirectassets.com"
_ADDRESS_NAMES = {"address and search bar", "地址和搜索栏"}
_CHALLENGE_MARKERS = (
    "verify you are human",
    "just a moment",
    "captcha",
    "hcaptcha",
    "recaptcha",
    "turnstile",
    "人机验证",
)
_BLOCKED_MARKERS = (
    "cpe00001",
    "there was a problem providing the content you requested",
)
_DENIED_MARKERS = (
    "you do not have access",
    "purchase pdf",
    "sign in to view",
)


class EdgeAutomationError(RuntimeError):
    pass


class EdgeUnavailableError(EdgeAutomationError):
    pass


class EdgeVerificationRequired(EdgeAutomationError):
    pass


class EdgeAccessBlocked(EdgeAutomationError):
    pass


class EdgeAccessDenied(EdgeAutomationError):
    pass


class EdgeInternalServerError(EdgeAutomationError):
    pass


class EdgeDownloadTooLarge(EdgeAutomationError):
    pass


@dataclass
class _EdgeSession:
    window: object
    article_url: str


class EdgeDesktopGateway:
    """编排普通 Edge 下载流程；同一桌面一次只允许处理一篇论文。"""

    _interaction_lock = threading.Lock()

    def __init__(self, adapter=None, sleep=None, monotonic=None, file_timeout=60):
        self._adapter = adapter or PywinautoEdgeAdapter()
        self._sleep = sleep or time.sleep
        self._monotonic = monotonic or time.monotonic
        self._file_timeout = max(1, int(file_timeout))

    @staticmethod
    def _validate_viewer_url(url, pii):
        parsed = urlparse(str(url or ""))
        query = parse_qs(parsed.query)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() != _PDF_HOST
            or query.get("pii") != [pii]
            or not parsed.path.lower().endswith(".pdf")
        ):
            raise EdgeAutomationError("Edge 打开的 PDF 地址与目标论文不一致")

    def _read_completed_pdf(self, path, max_pdf_size):
        deadline = self._monotonic() + self._file_timeout
        previous_size = None
        stable_count = 0
        while self._monotonic() < deadline:
            if path.is_file():
                size = path.stat().st_size
                if size > max_pdf_size:
                    raise EdgeDownloadTooLarge("PDF 文件超过 100 MB 上限")
                if size > 0 and size == previous_size:
                    stable_count += 1
                else:
                    stable_count = 0
                previous_size = size
                if stable_count >= 2:
                    content = path.read_bytes()
                    if not content.startswith(b"%PDF-"):
                        raise EdgeAutomationError("Edge 保存结果不是有效的 PDF 文件")
                    if b"%%EOF" not in content[-4096:]:
                        raise EdgeAutomationError("Edge 保存的 PDF 文件不完整")
                    return content
            self._sleep(0.5)
        raise EdgeAutomationError("等待 Edge 保存 PDF 超时")

    def download_pdf(self, article_url, pii, download_dir, max_pdf_size=100 * 1024 * 1024):
        download_root = Path(download_dir)
        download_root.mkdir(parents=True, exist_ok=True)
        destination = download_root / f".edge-download-{uuid4().hex}.pdf"
        session = None
        preserve_article = False
        thread_token = None

        with self._interaction_lock:
            try:
                initialize_thread = getattr(self._adapter, "initialize_thread", None)
                if initialize_thread is not None:
                    thread_token = initialize_thread()
                session = self._adapter.open_article(article_url)
                self._adapter.wait_until_download_available(session, pii)
                viewer_url = None
                for attempt in range(2):
                    self._adapter.click_view_pdf(session, pii)
                    try:
                        viewer_url = self._adapter.wait_for_pdf_viewer(session, pii)
                        break
                    except EdgeInternalServerError:
                        if attempt:
                            raise EdgeAccessBlocked("ScienceDirect PDF 页面连续返回内部错误")
                        self._adapter.refresh_article(session)
                        self._adapter.wait_until_download_available(session, pii)
                self._validate_viewer_url(viewer_url, pii)
                self._adapter.save_pdf(session, destination)
                return self._read_completed_pdf(destination, int(max_pdf_size))
            except EdgeVerificationRequired:
                preserve_article = True
                raise
            finally:
                try:
                    try:
                        if session is not None:
                            self._adapter.finish(session, preserve_article=preserve_article)
                    finally:
                        if destination.exists():
                            destination.unlink()
                finally:
                    uninitialize_thread = getattr(
                        self._adapter,
                        "uninitialize_thread",
                        None,
                    )
                    if uninitialize_thread is not None and thread_token is not None:
                        uninitialize_thread(thread_token)


class PywinautoEdgeAdapter:
    """封装 pywinauto 细节，所有页面动作都通过可见控件和真实输入完成。"""

    def __init__(self, sleep=None, monotonic=None, page_timeout=45, pdf_timeout=30):
        self._sleep = sleep or time.sleep
        self._monotonic = monotonic or time.monotonic
        self._page_timeout = max(1, int(page_timeout))
        self._pdf_timeout = max(1, int(pdf_timeout))

    @staticmethod
    def initialize_thread():
        """为当前任务线程初始化 COM，避免后台任务复用导入状态时失效。"""
        import sys

        already_imported = "comtypes" in sys.modules
        __import__("pywinauto")
        import comtypes

        if already_imported:
            comtypes.CoInitializeEx()
        return comtypes

    @staticmethod
    def uninitialize_thread(comtypes_module):
        comtypes_module.CoUninitialize()

    @staticmethod
    def _ui_modules():
        if os.name != "nt":
            raise EdgeUnavailableError("普通 Edge 桌面自动化仅支持 Windows")
        try:
            from pywinauto import Desktop, keyboard
        except ImportError as exc:
            raise EdgeUnavailableError("缺少 pywinauto，无法控制普通 Edge") from exc
        return Desktop, keyboard

    def _edge_windows(self):
        Desktop, _ = self._ui_modules()
        return Desktop(backend="uia").windows(
            class_name="Chrome_WidgetWin_1",
            visible_only=True,
        )

    @staticmethod
    def _control_value(control):
        try:
            return str(control.iface_value.CurrentValue or "")
        except Exception:
            try:
                return str(control.get_value() or "")
            except Exception:
                return ""

    def _address_control(self, window):
        for control in window.descendants(control_type="Edit"):
            name = str(control.element_info.name or "").strip().lower()
            if name in _ADDRESS_NAMES:
                return control
        return None

    def _address(self, window):
        control = self._address_control(window)
        return self._control_value(control) if control is not None else ""

    @staticmethod
    def _normalize_url(url):
        return str(url or "").rstrip("/")

    def _find_window_with_url(self, expected_url):
        expected = self._normalize_url(expected_url)
        for window in self._edge_windows():
            try:
                if self._normalize_url(self._address(window)) == expected:
                    return window
            except Exception:
                continue
        return None

    @staticmethod
    def _visible_enabled(control):
        try:
            return control.is_visible() and control.is_enabled()
        except Exception:
            return False

    def _view_pdf_control(self, window):
        for control in window.descendants(control_type="Hyperlink"):
            if control.element_info.name == _VIEW_PDF_NAME and self._visible_enabled(control):
                return control
        return None

    @staticmethod
    def _window_title(window):
        try:
            return str(window.window_text() or "")
        except Exception:
            return ""

    def _page_text(self, window):
        values = [self._window_title(window)]
        try:
            for control in window.descendants():
                if control.is_visible():
                    name = str(control.element_info.name or "").strip()
                    if name:
                        values.append(name)
        except Exception:
            pass
        return "\n".join(values).lower()

    def _raise_for_page(self, window):
        text = self._page_text(window)
        if any(marker in text for marker in _CHALLENGE_MARKERS):
            raise EdgeVerificationRequired(
                "ScienceDirect 要求人机验证，请在当前普通 Edge 页面手动完成后继续任务"
            )
        if any(marker in text for marker in _BLOCKED_MARKERS):
            raise EdgeAccessBlocked("ScienceDirect 拒绝了当前网络出口")
        if any(marker in text for marker in _DENIED_MARKERS):
            raise EdgeAccessDenied("当前机构会话没有该论文的全文访问权限")

    def open_article(self, article_url):
        edge_path = find_edge_executable()
        if edge_path is None:
            raise EdgeUnavailableError("未找到 Microsoft Edge")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen(
                [str(edge_path), "--profile-directory=Default", article_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        except OSError as exc:
            raise EdgeUnavailableError(f"无法启动 Microsoft Edge：{exc}") from exc

        deadline = self._monotonic() + self._page_timeout
        while self._monotonic() < deadline:
            window = self._find_window_with_url(article_url)
            if window is not None:
                window.set_focus()
                return _EdgeSession(window=window, article_url=article_url)
            self._sleep(0.5)
        raise EdgeUnavailableError("未能连接到普通 Edge 的目标文章标签页")

    def wait_until_download_available(self, session, pii):
        deadline = self._monotonic() + self._page_timeout
        while self._monotonic() < deadline:
            if self._normalize_url(self._address(session.window)) != self._normalize_url(
                session.article_url
            ):
                raise EdgeAutomationError("Edge 当前标签页已离开目标文章")
            control = self._view_pdf_control(session.window)
            if control is not None:
                return
            title = self._window_title(session.window).lower()
            if any(marker in title for marker in _CHALLENGE_MARKERS):
                self._raise_for_page(session.window)
            self._sleep(0.5)
        self._raise_for_page(session.window)
        raise EdgeAutomationError("等待 ScienceDirect 的 View PDF 控件超时")

    def click_view_pdf(self, session, pii):
        if self._normalize_url(self._address(session.window)) != self._normalize_url(
            session.article_url
        ):
            raise EdgeAutomationError("点击前 Edge 当前标签页已离开目标文章")
        control = self._view_pdf_control(session.window)
        if control is None:
            raise EdgeAutomationError("未找到可见的 View PDF 控件")
        session.window.set_focus()
        control.click_input()

    def wait_for_pdf_viewer(self, session, pii):
        deadline = self._monotonic() + self._pdf_timeout
        while self._monotonic() < deadline:
            url = self._address(session.window)
            parsed = urlparse(url)
            if (
                (parsed.hostname or "").lower() == _PDF_HOST
                and parse_qs(parsed.query).get("pii") == [pii]
            ):
                session.window.set_focus()
                return url
            title = self._window_title(session.window).lower()
            if "internal server error" in title:
                raise EdgeInternalServerError("ScienceDirect PDF 页面返回 Internal Server Error")
            if any(marker in title for marker in _CHALLENGE_MARKERS):
                self._raise_for_page(session.window)
            self._sleep(0.5)
        self._raise_for_page(session.window)
        raise EdgeAutomationError("等待 Edge PDF 查看器超时")

    def refresh_article(self, session):
        _, keyboard = self._ui_modules()
        session.window.set_focus()
        if "internal server error" in self._window_title(session.window).lower():
            keyboard.send_keys("^w")
            self._sleep(1)
        window = self._find_window_with_url(session.article_url)
        if window is None:
            raise EdgeAutomationError("关闭错误页后未找到目标文章标签页")
        session.window = window
        window.set_focus()
        keyboard.send_keys("{F5}")

    @staticmethod
    def _find_by_automation_id(window, automation_id, class_name=None):
        for control in window.descendants():
            info = control.element_info
            if (
                str(info.automation_id or "") == str(automation_id)
                and (class_name is None or info.class_name == class_name)
            ):
                return control
        return None

    def save_pdf(self, session, destination):
        _, keyboard = self._ui_modules()
        destination = Path(destination).resolve()
        session.window.set_focus()
        keyboard.send_keys("^s")

        deadline = self._monotonic() + 15
        filename = None
        save_button = None
        while self._monotonic() < deadline:
            filename = self._find_by_automation_id(session.window, "1001", "Edit")
            save_button = self._find_by_automation_id(session.window, "1", "Button")
            if filename is not None and save_button is not None:
                break
            self._sleep(0.25)
        if filename is None or save_button is None:
            raise EdgeAutomationError("Edge 未打开 PDF 另存为窗口")

        filename.click_input()
        keyboard.send_keys("^a")
        keyboard.send_keys(str(destination), with_spaces=True)
        save_button.click_input()

    def finish(self, session, preserve_article=False):
        if preserve_article:
            return
        _, keyboard = self._ui_modules()
        try:
            session.window.set_focus()
            if self._find_by_automation_id(session.window, "1001", "Edit") is not None:
                keyboard.send_keys("{ESC}")
                self._sleep(0.25)
            parsed = urlparse(self._address(session.window))
            if (parsed.hostname or "").lower() == _PDF_HOST:
                keyboard.send_keys("^w")
                self._sleep(0.5)
            article_window = self._find_window_with_url(session.article_url)
            if article_window is not None:
                article_window.set_focus()
                keyboard.send_keys("^w")
        except Exception:
            # 标签清理失败不应覆盖已经确定的下载结果或原始错误。
            return
