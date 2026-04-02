import contextlib
import io
import importlib.util
import json
from pathlib import Path
import sys

import requests

from app.crawler.providers.base import ProviderError
from app.crawler.runtime.paths import get_legacy_crawler_root


class DomesticCrawlerProvider:
    def __init__(self, crawler_factory=None, enable_network_precheck=None, precheck_timeout=8):
        self._crawler_factory = crawler_factory
        self._default_script_path = None
        self._enable_network_precheck = (
            crawler_factory is None if enable_network_precheck is None else bool(enable_network_precheck)
        )
        self._precheck_timeout = max(1, int(precheck_timeout))
        self._precheck_url = "https://www.ncpssd.cn"

    def _load_default_factory(self):
        script_path = self._default_script_path or (
            get_legacy_crawler_root() / "domestic" / "0.journal_paper_info_crawler.py"
        )
        script_path = Path(script_path)
        spec = importlib.util.spec_from_file_location("domestic_crawler_module", script_path)
        module = importlib.util.module_from_spec(spec)
        parent_dir = str(script_path.parent)
        restore_path = False
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            restore_path = True
        try:
            spec.loader.exec_module(module)
        finally:
            if restore_path and sys.path and sys.path[0] == parent_dir:
                sys.path.pop(0)
        return module.JournalPaperInfoCrawler

    def _get_factory(self):
        return self._crawler_factory or self._load_default_factory()

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
                "Domestic network precheck failed: 无法访问 ncpssd.cn。请关闭 VPN，"
                "或将 *.ncpssd.cn 配置为直连后重试。"
                f" 原始错误: {exc}"
            ) from exc
        if response.status_code >= 500:
            raise ProviderError(
                "Domestic network precheck failed: ncpssd.cn 返回异常状态。"
                " 请确认当前网络可直连国内站点后重试。"
                f" status={response.status_code}"
            )

    def fetch_issue(self, journal_name, year, issue):
        self._network_precheck()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            crawler = self._get_factory()()
            result = crawler.crawl_journal_papers(journal_name, year, issue)
        if not result.get("success"):
            raise ProviderError(result.get("error_message") or "Domestic crawl failed")

        papers = []
        for index, paper in enumerate(result.get("papers", [])):
            keywords = paper.get("keywords", [])
            papers.append(
                {
                    "source_identifier": paper.get("detail_url") or f"{journal_name}-{year}-{issue}-{index}",
                    "title": paper.get("title", ""),
                    "title_zh": paper.get("title_zh"),
                    "authors": paper.get("authors"),
                    "abstract": paper.get("abstract"),
                    "abstract_zh": paper.get("abstract_zh"),
                    "keywords_json": json.dumps(keywords, ensure_ascii=False),
                    "pages": paper.get("pages"),
                    "detail_url": paper.get("detail_url"),
                    "published_at": paper.get("published_at"),
                    "sort_index": paper.get("sort_index", index),
                    "translation_status": "completed" if paper.get("title_zh") else "pending",
                }
            )

        return {
            "issue": {
                "source_type": "domestic",
                "journal_name": result["journal_name"],
                "journal_slug": result["journal_name"],
                "year": result["year"],
                "issue": str(result["issue"]),
                "language": "zh",
                "source_url": result.get("issue_url"),
            },
            "papers": papers,
        }
