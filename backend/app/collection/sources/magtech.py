"""Magtech（玛格泰克）期刊官网采集源。

Magtech 是国内期刊站点常见的建站系统，各站点接口路径一致，因此本源按 ``base_url``
配置即可服务多个期刊。全部接口均为 HTTP GET，不依赖浏览器自动化。

已实测的站点接口（以《情报学报》https://qbxb.istic.ac.cn 为例）：

- 年 → 期列表：``GET {base}/CN/article/showTenYearVolumnDetail.do?nian={year}``
- 期 → 文章 id：``GET {base}/CN/volumn/volumn_{volumn_id}.shtml``
- 题录字段：``GET {base}/CN/article/getTxtFile.do?fileType=BibTeX&id={article_id}``
- 摘要正文：``GET {base}/CN/article/getTxtFile.do?fileType=EndNote&id={article_id}``
- 全文 PDF：``GET {base}/CN/article/downloadArticleFile.do?attachType=PDF&id={article_id}``

BibTeX 不含摘要，EndNote（RIS）不含关键词，两者互补，因此每篇文章需要两次请求。
"""
import html
import json
import re
import time

import requests

from app.core.text import clean_title_text
from app.collection.sources.base import ProviderError, SourceAdapter, check_result

YEAR_PAGE_URL = "{base}/CN/article/showTenYearVolumnDetail.do?nian={year}"
VOLUMN_PAGE_URL = "{base}/CN/volumn/volumn_{volumn_id}.shtml"
EXPORT_URL = "{base}/CN/article/getTxtFile.do?fileType={file_type}&id={article_id}"
PDF_URL = "{base}/CN/article/downloadArticleFile.do?attachType=PDF&id={article_id}"
ABSTRACT_PAGE_URL = "{base}/CN/abstract/abstract{article_id}.shtml"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# 年页里同时存在「封面图区块」与「文字列表区块」两组相同的 volumn 链接，
# 只有文字列表的链接文本带有卷期描述，靠描述正则把封面行过滤掉。
_ISSUE_LINK_RE = re.compile(r'<a[^>]*volumn_(\d+)\.shtml"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_ISSUE_DESC_RE = re.compile(
    r"(\d{4})\s*Vol\.?\s*([^\s]+)\s*No\.?\s*(\d+)\s*(?:pp\.?\s*([\d\-]+))?\s*(\d{4}-\d{2}-\d{2})?",
    re.IGNORECASE,
)
_ARTICLE_ID_RE = re.compile(r"abstract(\d+)\.shtml")
_BIBTEX_FIELD_RE = re.compile(r"(\w+)\s*=\s*\{(.*?)\}", re.DOTALL)


def _strip_tags(fragment):
    """把 HTML 片段压成单行纯文本，用于匹配站点里的卷期描述。"""
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_year_page(page_html, year=None):
    """解析按年查询的期号列表页，返回按期号升序排列的期号信息。"""
    issues = {}
    for volumn_id, fragment in _ISSUE_LINK_RE.findall(page_html or ""):
        match = _ISSUE_DESC_RE.search(_strip_tags(fragment))
        if not match:
            continue
        row_year, volume, issue, pages, published_at = match.groups()
        if year is not None and int(row_year) != int(year):
            # 站点模板里可能混入其他期刊/年份的残留内容，按年份过滤掉
            continue
        issues[str(int(issue))] = {
            "volumn_id": volumn_id,
            "year": int(row_year),
            "volume": volume.strip(),
            "issue": str(int(issue)),
            "pages": pages or "",
            "published_at": published_at or "",
        }
    return [issues[key] for key in sorted(issues, key=int)]


def parse_volumn_page(page_html):
    """解析某一期的目录页，按出现顺序返回去重后的文章 id。"""
    ordered = []
    for article_id in _ARTICLE_ID_RE.findall(page_html or ""):
        if article_id not in ordered:
            ordered.append(article_id)
    return ordered


def parse_bibtex(text):
    """解析 BibTeX 导出，得到题录字段。"""
    fields = {}
    for key, value in _BIBTEX_FIELD_RE.findall(text or ""):
        fields[key.strip().lower()] = value.strip()

    keywords = [item.strip() for item in (fields.get("keywords") or "").split(";") if item.strip()]
    return {
        "title": clean_title_text(fields.get("title", "")),
        "authors": fields.get("author", ""),
        "journal": fields.get("journal") or fields.get("publisher", ""),
        "year": fields.get("year", ""),
        "volume": fields.get("volume", ""),
        "number": fields.get("number", ""),
        "pages": fields.get("pages", ""),
        "doi": fields.get("doi", ""),
        "url": fields.get("url", ""),
        "keywords": keywords,
    }


def parse_endnote(text):
    """解析 EndNote（RIS）导出，主要取摘要与出版日期。

    RIS 的摘要可能折行，标签行之后的非标签行按续行接到上一个标签末尾。
    """
    values = {}
    current_tag = None
    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        if line.startswith("%") and len(line) > 2 and line[2] == " ":
            current_tag = line[1]
            value = line[3:].strip()
            values.setdefault(current_tag, [])
            if value:
                values[current_tag].append(value)
        elif current_tag and line.strip():
            if values.get(current_tag):
                values[current_tag][-1] += line.strip()
            else:
                values[current_tag] = [line.strip()]

    def first(tag):
        items = values.get(tag) or []
        return items[0] if items else ""

    return {
        "abstract": "\n".join(values.get("X") or []),
        "pages": first("P"),
        "published_at": first("8"),
    }


class MagtechSource(SourceAdapter):
    source_id = "magtech"
    display_name = "期刊官网（Magtech）"
    region = "domestic"
    metadata_priority = 300
    capabilities = {
        "list_issues": True,
        "download_pdf": True,
        "needs_browser": False,
    }
    config_fields = [
        {
            "key": "base_url",
            "label": "期刊官网地址",
            "required": True,
            "placeholder": "https://qbxb.istic.ac.cn",
            "help": "Magtech 站点根地址，不要带结尾斜杠",
        }
    ]

    def __init__(
        self,
        base_url=None,
        session=None,
        request_interval=0.5,
        timeout=15,
        max_attempts=3,
    ):
        if not base_url:
            raise ValueError("MagtechSource 需要 base_url 配置")
        self.base_url = str(base_url).rstrip("/")
        self._session = session or requests.Session()
        self._session.trust_env = False
        self._request_interval = max(0.0, float(request_interval))
        self._timeout = timeout
        self._max_attempts = max(1, int(max_attempts))

    def _request(self, url):
        last_error = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._session.get(url, timeout=self._timeout, headers=DEFAULT_HEADERS)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    break
                time.sleep(self._request_interval * attempt)
                continue

            status = getattr(response, "status_code", 200)
            if 400 <= status < 500 and status != 429:
                # 4xx 是确定性失败（如文章 id 不存在），重试没有意义
                raise ProviderError(f"Magtech 请求被拒绝：{url}（HTTP {status}）")
            if status >= 500:
                last_error = requests.HTTPError(f"HTTP {status}")
                if attempt >= self._max_attempts:
                    break
                time.sleep(self._request_interval * attempt)
                continue

            response.raise_for_status()
            if self._request_interval:
                time.sleep(self._request_interval)
            return response

        raise ProviderError(
            f"Magtech 请求失败，已尝试 {self._max_attempts} 次：{url} —— {last_error}"
        )

    def _get(self, url):
        return self._request(url).text

    def list_issues(self, journal_name, year, **kwargs):
        page_html = self._get(YEAR_PAGE_URL.format(base=self.base_url, year=year))
        issues = parse_year_page(page_html, year)
        for item in issues:
            item["source_url"] = VOLUMN_PAGE_URL.format(base=self.base_url, volumn_id=item["volumn_id"])
        return issues

    def fetch_issue(self, journal_name, year, issue, **kwargs):
        volumn = self._resolve_volumn(year, issue)
        page_html = self._get(volumn["source_url"])
        article_ids = parse_volumn_page(page_html)

        papers = []
        for index, article_id in enumerate(article_ids):
            paper = self._build_paper(article_id, index)
            if paper:
                papers.append(paper)

        return {
            "issue": {
                "source_type": self.source_id,
                "region": self.region,
                "journal_name": journal_name,
                "journal_slug": journal_name,
                "year": int(year),
                "issue": str(issue),
                "volume": volumn.get("volume"),
                "language": "zh",
                "source_url": volumn["source_url"],
                "paper_count_hint": len(article_ids),
            },
            "papers": papers,
        }

    def download_pdf(self, paper_ref, **kwargs):
        """下载单篇 PDF，文件校验与落盘由全文服务统一处理。"""
        from app.collection.sources.base import PdfDownload

        article_id = paper_ref if isinstance(paper_ref, (str, int)) else paper_ref.get("article_id")
        if not article_id:
            raise ProviderError("下载 PDF 需要文章 id")
        url = PDF_URL.format(base=self.base_url, article_id=article_id)
        response = self._request(url)
        return PdfDownload(
            content=response.content,
            source_url=url,
            content_type=response.headers.get("Content-Type"),
        )

    def test_connection(self, **kwargs):
        """取回站点可识别的信息，让用户确认没有填错地址。"""
        year = kwargs.get("year")
        from datetime import date

        year = year or date.today().year
        try:
            issues = self.list_issues(None, year)
        except ProviderError as exc:
            return check_result("failed", str(exc))

        if not issues:
            return check_result(
                "warn",
                f"可以访问 {self.base_url}，但未解析到 {year} 年的期号，"
                "请确认地址是否为该期刊的 Magtech 官网。",
            )

        latest = issues[-1]
        return check_result(
            "ok",
            f"已连通，识别到 {year} 年共 {len(issues)} 期，"
            f"最新为第 {latest['issue']} 期（Vol.{latest['volume']}，出版日期 {latest['published_at']}）。",
        )

    def _resolve_volumn(self, year, issue):
        target = self._normalize_issue(issue)
        for item in self.list_issues(None, year):
            if item["issue"] == target:
                return item
        raise ProviderError(
            f"未在 {self.base_url} 上找到 {year} 年第 {issue} 期。"
            "请确认年份与期号；若年份较早，该站点可能只提供近十年的目录。"
        )

    def _build_paper(self, article_id, index):
        bibtex_url = EXPORT_URL.format(base=self.base_url, file_type="BibTeX", article_id=article_id)
        endnote_url = EXPORT_URL.format(base=self.base_url, file_type="EndNote", article_id=article_id)
        try:
            metadata = parse_bibtex(self._get(bibtex_url))
            extra = parse_endnote(self._get(endnote_url))
        except ProviderError:
            # 单篇题录拉取失败不应让整期采集失败，跳过该篇
            return None

        title = metadata["title"]
        if not title:
            return None

        abstract = extra["abstract"]
        # BibTeX 的 url 可能仍使用会落入软 404 的 article_{id} 旧格式。
        detail_url = ABSTRACT_PAGE_URL.format(base=self.base_url, article_id=article_id)
        doi = metadata["doi"]
        return {
            "source_identifier": doi or detail_url,
            "source_ref_json": json.dumps({"article_id": article_id}, ensure_ascii=False),
            "title": title,
            "title_zh": title,
            "authors": metadata["authors"],
            "abstract": abstract,
            "abstract_zh": abstract,
            "keywords_json": json.dumps(metadata["keywords"], ensure_ascii=False),
            "pages": extra["pages"] or metadata["pages"],
            "doi": doi,
            "detail_url": detail_url,
            "published_at": extra["published_at"],
            "sort_index": index,
            "translation_status": "completed",
        }

    @staticmethod
    def _normalize_issue(issue):
        try:
            return str(int(str(issue).strip()))
        except (TypeError, ValueError):
            return str(issue).strip()
