"""Scopus Search API 年度题录采集源。"""
import json
import os
import time

import requests
from dotenv import dotenv_values

from app.collection.sources.base import ProviderError, SourceAdapter, check_result
from app.core.paths import workspace_root


SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
PAGE_SIZE = 25
MAX_START = 5000


def load_elsevier_api_key(env_path=None):
    """每次调用都读取当前环境与根目录 .env，设置页更新后无需重启。"""
    value = os.environ.get("ELSEVIER_API_KEY")
    if isinstance(value, str) and value.strip():
        return value.strip()
    path = env_path or workspace_root() / ".env"
    if not path.exists():
        return None
    value = dotenv_values(path, encoding="utf-8").get("ELSEVIER_API_KEY")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _clean(value):
    return str(value).strip() if value not in (None, "") else None


def _author_name(author):
    explicit = _clean(author.get("authname"))
    if explicit:
        return explicit
    return " ".join(
        part for part in (_clean(author.get("given-name")), _clean(author.get("surname"))) if part
    ) or None


class ScopusSource(SourceAdapter):
    """按 ISSN 与出版年拉取 Scopus COMPLETE 题录。"""

    source_id = "scopus"
    display_name = "Scopus API"
    region = "foreign"
    metadata_priority = 250
    ingest_scope = "year"
    capabilities = {
        "list_issues": False,
        "download_pdf": False,
        "needs_browser": False,
    }
    config_fields = []

    def __init__(
        self,
        api_key_loader=None,
        session_factory=None,
        sleep=None,
        timeout=60,
        max_retries=3,
    ):
        self._api_key_loader = api_key_loader or load_elsevier_api_key
        self._session_factory = session_factory or requests.Session
        self._sleep = sleep or time.sleep
        self._timeout = timeout
        self._max_retries = max(1, int(max_retries))

    def _credentials(self, issn):
        api_key = self._api_key_loader()
        if not api_key:
            raise ProviderError("未配置 Elsevier Research Products API Key")
        cleaned_issn = _clean(issn)
        if not cleaned_issn:
            raise ProviderError("Scopus 采集需要期刊 ISSN")
        return api_key, cleaned_issn

    def _request(self, session, api_key, params):
        headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
        for attempt in range(self._max_retries):
            try:
                response = session.get(
                    SCOPUS_SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                if attempt + 1 >= self._max_retries:
                    raise ProviderError(f"Scopus 请求失败：{exc}") from exc
                self._sleep(2**attempt)
                continue

            if response.status_code in (401, 403):
                raise ProviderError(
                    "Scopus COMPLETE 权限校验失败，请确认 API Key 有效，并通过校园网或 aTrust 直连后重试"
                )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt + 1 >= self._max_retries:
                    raise ProviderError(f"Scopus 服务暂不可用（HTTP {response.status_code}）")
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = max(float(retry_after), 0.0)
                except (TypeError, ValueError):
                    delay = float(2**attempt)
                self._sleep(delay)
                continue
            if response.status_code >= 400:
                raise ProviderError(f"Scopus 请求失败（HTTP {response.status_code}）")
            try:
                return response.json()
            except ValueError as exc:
                raise ProviderError("Scopus 返回了无法解析的 JSON") from exc
        raise ProviderError("Scopus 请求重试次数已耗尽")

    def _map_entry(self, entry, sort_index):
        title = _clean(entry.get("dc:title"))
        eid = _clean(entry.get("eid"))
        pii = _clean(entry.get("pii"))
        doi = _clean(entry.get("prism:doi"))
        if not title or not (eid or doi or pii):
            return None

        authors = [name for name in (_author_name(item) for item in entry.get("author") or []) if name]
        if not authors:
            creator = _clean(entry.get("dc:creator"))
            authors = [creator] if creator else []

        keywords = [
            keyword.strip()
            for keyword in str(entry.get("authkeywords") or "").split("|")
            if keyword.strip()
        ]
        pages = _clean(entry.get("prism:pageRange"))
        if not pages:
            start_page = _clean(entry.get("prism:startingPage"))
            end_page = _clean(entry.get("prism:endingPage"))
            pages = "-".join(part for part in (start_page, end_page) if part) or None

        refs = {key: value for key, value in (("eid", eid), ("pii", pii), ("doi", doi)) if value}
        detail_url = None
        if pii:
            detail_url = f"https://www.sciencedirect.com/science/article/pii/{pii}"
        elif doi:
            detail_url = f"https://doi.org/{doi}"

        return {
            "source_identifier": eid or _clean(entry.get("dc:identifier")),
            "source_ref_json": json.dumps(refs, ensure_ascii=False),
            "title": title,
            "authors": ", ".join(authors) or None,
            "abstract": _clean(entry.get("dc:description")),
            "keywords_json": json.dumps(keywords, ensure_ascii=False),
            "pages": pages,
            "doi": doi,
            "detail_url": detail_url,
            "published_at": _clean(entry.get("prism:coverDate")),
            "volume": _clean(entry.get("prism:volume")),
            "issue": _clean(entry.get("prism:issueIdentifier")),
            "sort_index": sort_index,
            "translation_status": "pending",
        }

    @staticmethod
    def _dedupe_key(paper):
        refs = json.loads(paper["source_ref_json"])
        for key in ("eid", "doi", "pii"):
            value = refs.get(key)
            if value:
                return key, value.casefold()
        return None

    def _search(self, journal_name, year, issn, view, count, paginate=True):
        api_key, cleaned_issn = self._credentials(issn)
        session = self._session_factory()
        session.trust_env = False
        query = f"ISSN({cleaned_issn}) AND PUBYEAR = {int(year)}"
        papers = []
        seen = set()
        dropped = 0
        fetched = 0
        total = 0
        start = 0

        while True:
            if start >= MAX_START:
                raise ProviderError(
                    f"Scopus 结果超过 {MAX_START} 条分页上限，年度采集已停止以避免静默截断"
                )
            params = {
                "query": query,
                "view": view,
                "sort": "coverDate",
                "count": count,
                "start": start,
            }
            payload = self._request(session, api_key, params)
            search_results = payload.get("search-results") or {}
            try:
                total = max(int(search_results.get("opensearch:totalResults") or 0), 0)
            except (TypeError, ValueError):
                total = 0
            entries = search_results.get("entry") or []
            fetched += len(entries)
            for entry in entries:
                paper = self._map_entry(entry, len(papers))
                if paper is None:
                    dropped += 1
                    continue
                key = self._dedupe_key(paper)
                if key in seen:
                    dropped += 1
                    continue
                seen.add(key)
                papers.append(paper)

            if not paginate or fetched >= total or not entries:
                break
            start += count
            self._sleep(0.5)

        return {
            "issue": {
                "source_type": self.source_id,
                "region": self.region,
                "journal_name": journal_name,
                "year": int(year),
                "issue": "year",
                "volume": None,
                "language": "en",
                "source_url": SCOPUS_SEARCH_URL,
                "paper_count_hint": total,
                "dropped_paper_count": dropped,
            },
            "papers": papers,
        }

    def fetch_issue(self, journal_name, year, issue, **kwargs):
        return self._search(journal_name, year, kwargs.get("issn"), "COMPLETE", PAGE_SIZE)

    def test_connection(self, **kwargs):
        try:
            payload = self._search(
                kwargs.get("journal_name") or "",
                time.localtime().tm_year,
                kwargs.get("issn"),
                "STANDARD",
                1,
                paginate=False,
            )
        except ProviderError as exc:
            return check_result("failed", str(exc))
        total = payload["issue"]["paper_count_hint"]
        return check_result("ok", f"Scopus API 已连通，当前年度检索到 {total} 条记录")
