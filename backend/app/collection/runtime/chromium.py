"""受控 Chromium 会话，用于用户手动完成登录或人机校验。"""

import socket
import threading

from app.collection.runtime.paths import find_chrome_executable, get_browser_data_root


class BrowserUnavailableError(RuntimeError):
    pass


class ChromiumSessionGateway:
    def __init__(self, port=9222, page_factory=None):
        self.port = int(port)
        self._page_factory = page_factory
        self._page = None
        self._lock = threading.Lock()

    def _is_port_open(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        try:
            return sock.connect_ex(("127.0.0.1", self.port)) == 0
        finally:
            sock.close()

    def _connect(self, allow_launch):
        if self._page is not None:
            try:
                self._page.url
                return self._page
            except Exception:
                self._page = None

        if self._page_factory:
            self._page = self._page_factory()
            return self._page

        from DrissionPage import ChromiumOptions, ChromiumPage

        options = ChromiumOptions()
        options.set_local_port(self.port)
        if self._is_port_open():
            if hasattr(options, "existing_only"):
                options.existing_only(True)
        elif allow_launch:
            browser_path = find_chrome_executable()
            if browser_path is None:
                raise BrowserUnavailableError(
                    "未找到可用的 Chromium 浏览器，请配置 CRAWLER_BROWSER_PATH"
                )
            profile_root = get_browser_data_root()
            profile_root.mkdir(parents=True, exist_ok=True)
            options.set_browser_path(str(browser_path))
            options.set_user_data_path(str(profile_root))
        else:
            return None

        try:
            self._page = ChromiumPage(options)
        except Exception as exc:
            raise BrowserUnavailableError(f"无法连接受控浏览器：{exc}") from exc
        return self._page

    def open_for_verification(self, url):
        with self._lock:
            page = self._connect(allow_launch=True)
            page.get(url)

    def session_state(self):
        """只在内存中返回请求所需会话，不持久化 Cookie 或浏览器指纹。"""
        with self._lock:
            try:
                page = self._connect(allow_launch=False)
            except BrowserUnavailableError:
                return {"user_agent": None, "cookies": []}
            if page is None:
                return {"user_agent": None, "cookies": []}
            return {
                "user_agent": page.user_agent,
                "cookies": list(page.cookies(all_domains=True, all_info=True)),
            }
