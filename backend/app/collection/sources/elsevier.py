import contextlib
import io
import importlib.util
from pathlib import Path
import socket
import sys

import requests

from app.collection.sources.base import ProviderError
from app.collection.runtime.paths import find_chrome_executable, get_browser_data_root, get_legacy_crawler_root


class ElsevierSource:
    def __init__(
        self,
        mapper_factory=None,
        crawler_factory=None,
        journal_slugs=None,
        base_url=None,
        enable_network_precheck=None,
        precheck_timeout=8,
    ):
        self._mapper_factory = mapper_factory
        self._crawler_factory = crawler_factory
        self._journal_slugs = journal_slugs
        self._base_url = base_url
        self._enable_network_precheck = (
            mapper_factory is None and crawler_factory is None
            if enable_network_precheck is None
            else bool(enable_network_precheck)
        )
        self._precheck_timeout = max(1, int(precheck_timeout))
        self._precheck_url = "https://www.sciencedirect.com"

    def _import_module(self, name, relative_parts):
        path = Path(*relative_parts)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        parent_dir = str(path.parent)
        restore_path = False
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            restore_path = True
        try:
            spec.loader.exec_module(module)
        finally:
            if restore_path and sys.path and sys.path[0] == parent_dir:
                sys.path.pop(0)
        return module

    def _get_mapper_factory(self):
        if self._mapper_factory:
            return self._mapper_factory
        legacy_root = get_legacy_crawler_root()
        module = self._import_module(
            "foreign_volume_mapper",
            [legacy_root, "foreign", "1.vol_year_mapper.py"],
        )
        return self._wrap_legacy_browser_client(module, module.VolumeYearMapper, "VolumeYearMapper")

    def _get_crawler_factory(self):
        if self._crawler_factory:
            return self._crawler_factory
        legacy_root = get_legacy_crawler_root()
        module = self._import_module(
            "foreign_issue_crawler",
            [legacy_root, "foreign", "2.issue_crawler.py"],
        )
        return self._wrap_legacy_browser_client(module, module.IssueCrawler, "IssueCrawler")

    def _get_config(self):
        if self._journal_slugs is not None and self._base_url is not None:
            return self._journal_slugs, self._base_url
        legacy_root = get_legacy_crawler_root()
        module = self._import_module(
            "foreign_config",
            [legacy_root, "foreign", "config_foreign.py"],
        )
        return module.JOURNAL_SLUGS, module.BASE_URL

    def _wrap_legacy_browser_client(self, module, base_class, class_name):
        provider = self
        browser_path = find_chrome_executable()
        profile_root = get_browser_data_root()

        class ManagedLegacyBrowserClient(base_class):
            def _init_page(self_inner):
                if getattr(self_inner, "page", None):
                    return
                self_inner.page = provider._create_chromium_page(module, browser_path, profile_root)

        ManagedLegacyBrowserClient.__name__ = class_name
        return ManagedLegacyBrowserClient

    def _create_chromium_page(self, module, browser_path, profile_root):
        if not self._is_debug_port_open(9222):
            return self._launch_chromium_page(module, browser_path, profile_root)

        attach_error = None

        attach_options = module.ChromiumOptions()
        attach_options.set_local_port(9222)
        if hasattr(attach_options, "existing_only"):
            attach_options.existing_only(True)
        try:
            return module.ChromiumPage(attach_options)
        except Exception as exc:
            attach_error = exc

        return self._launch_chromium_page(module, browser_path, profile_root, attach_error)

    def _launch_chromium_page(self, module, browser_path, profile_root, attach_error=None):
        profile_root.mkdir(parents=True, exist_ok=True)
        launch_options = module.ChromiumOptions()
        launch_options.set_local_port(9222)
        launch_options.set_user_data_path(str(profile_root))
        if browser_path:
            launch_options.set_browser_path(str(browser_path))
        try:
            return module.ChromiumPage(launch_options)
        except Exception as launch_error:
            raise RuntimeError(
                f"Attach mode failed: {attach_error}; launch mode failed: {launch_error}"
            ) from launch_error

    def _is_debug_port_open(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        try:
            return sock.connect_ex(("127.0.0.1", port)) == 0
        finally:
            sock.close()

    def _network_precheck(self):
        if not self._enable_network_precheck:
            return
        try:
            response = requests.get(
                self._precheck_url,
                timeout=self._precheck_timeout,
                headers={"User-Agent": "Mozilla/5.0"},
            )
        except requests.RequestException as exc:
            raise ProviderError(
                "Foreign network precheck failed: 无法访问 sciencedirect.com。"
                " 请开启 VPN 或可用代理后重试。"
                f" 原始错误: {exc}"
            ) from exc
        if response.status_code >= 500:
            raise ProviderError(
                "Foreign network precheck failed: sciencedirect.com 返回异常状态。"
                " 请确认 VPN/代理可访问外网后重试。"
                f" status={response.status_code}"
            )

    def fetch_issue(self, journal_name, year, issue):
        journal_slugs, base_url = self._get_config()
        slug = journal_slugs.get(journal_name)
        if not slug:
            raise ProviderError(f"Unknown journal: {journal_name}")

        self._network_precheck()

        mapper = self._get_mapper_factory()()
        volume = mapper.get_calculated_volume(journal_name, year)
        if not volume:
            raise ProviderError(f"Unable to determine volume for {journal_name} {year}")

        source_url = f"{base_url}/journal/{slug}/vol/{volume}/issue/{issue}"

        crawl_logs = ""
        try:
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                crawler = self._get_crawler_factory()()
                papers = crawler.crawl_issue(source_url)
            crawl_logs = "\n".join(
                line for line in (stdout_buffer.getvalue() + "\n" + stderr_buffer.getvalue()).splitlines() if line.strip()
            )
        except Exception as exc:
            raise ProviderError(f"Foreign crawl failed: {exc}") from exc
        if not papers:
            hint = ""
            if crawl_logs:
                tail = "\n".join(crawl_logs.splitlines()[-6:])
                hint = f"\nCrawler logs:\n{tail}"
            raise ProviderError(
                "Foreign crawl returned zero papers. This is usually caused by anti-bot challenge or parser selector mismatch."
                + hint
            )

        return {
            "issue": {
                "source_type": "foreign",
                "journal_name": journal_name,
                "journal_slug": slug,
                "year": year,
                "issue": str(issue),
                "volume": str(volume),
                "language": "en",
                "source_url": source_url,
            },
            "papers": [
                {
                    "source_identifier": paper.get("detail_url") or f"{slug}-{year}-{issue}-{index}",
                    "title": paper.get("title", ""),
                    "title_zh": paper.get("title_zh", ""),
                    "authors": paper.get("authors"),
                    "abstract": paper.get("abstract"),
                    "abstract_zh": paper.get("abstract_zh", ""),
                    "keywords_json": paper.get("keywords_json"),
                    "pages": paper.get("pages"),
                    "detail_url": paper.get("detail_url"),
                    "published_at": paper.get("published_at"),
                    "sort_index": paper.get("sort_index", index),
                    "translation_status": "completed" if paper.get("title_zh") else "pending",
                }
                for index, paper in enumerate(papers)
            ],
        }
