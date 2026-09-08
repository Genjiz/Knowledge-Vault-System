import contextlib
import io
import importlib.util
import json
from pathlib import Path
import sys

import requests

from app.collection.sources.base import ProviderError, SourceAdapter, check_result
from app.collection.runtime.paths import get_legacy_crawler_root

# 期刊定位参数缓存由 legacy 抓取脚本维护，测试连接时据此判断期刊是否被收录
JOURNAL_URL_CACHE_NAME = "journal_url_cache.json"


class NcpssdSource(SourceAdapter):
    """国家哲学社会科学文献中心采集源（包装 legacy 抓取脚本）。"""

    source_id = "ncpssd"
    display_name = "国家哲社文献中心"
    region = "domestic"
    metadata_priority = 200
    capabilities = {
        "list_issues": False,
        "download_pdf": False,
        "needs_browser": True,
    }
    # 期刊定位参数由 legacy/domestic/journal_url_cache.json 缓存解析，无需用户配置
    config_fields = []

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

    def test_connection(self, **kwargs):
        """校验期刊定位参数是否已缓存，并预检站点可达性。

        期刊未收录时定位参数缺失，采集必然失败，因此这里给出 warn 而非 ok，
        让用户先补参数再发起采集。
        """
        journal_name = kwargs.get("journal_name")
        if journal_name and not self._cached_journal_param(journal_name):
            return check_result(
                "warn",
                f"NCPSSD 未收录《{journal_name}》：{JOURNAL_URL_CACHE_NAME} 中没有该期刊的"
                "定位参数，需先补参数再采集。",
            )

        try:
            self._network_precheck()
        except ProviderError as exc:
            return check_result("failed", str(exc))

        if journal_name:
            return check_result("ok", f"站点可达，《{journal_name}》已收录，定位参数已缓存")
        return check_result("ok", "站点可达")

    def _cached_journal_param(self, journal_name):
        cache_path = Path(get_legacy_crawler_root()) / "domestic" / JOURNAL_URL_CACHE_NAME
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return cache.get(journal_name)

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
                "source_type": self.source_id,
                "region": self.region,
                "journal_name": result["journal_name"],
                "journal_slug": result["journal_name"],
                "year": result["year"],
                "issue": str(result["issue"]),
                "language": "zh",
                "source_url": result.get("issue_url"),
            },
            "papers": papers,
        }
