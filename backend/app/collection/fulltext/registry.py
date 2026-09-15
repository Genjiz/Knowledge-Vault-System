"""根据原始论文稳定引用选择全文提供器。"""

import json
import re
from urllib.parse import urlparse

from app.collection.fulltext.base import FullTextReference


_MAGTECH_ARTICLE_RE = re.compile(r"(?:article_|abstract)(\d+)\.shtml", re.IGNORECASE)
_SCIENCEDIRECT_PII_RE = re.compile(r"/pii/([^/?#]+)", re.IGNORECASE)
_COMPACT_PII_RE = re.compile(r"^S[0-9X]{16}$", re.IGNORECASE)
_LEGACY_PII_RE = re.compile(
    r"^S[0-9X]{4}-[0-9X]{4}\([0-9]{2}\)[0-9]{5}-[0-9X]$",
    re.IGNORECASE,
)


def _source_refs(raw_paper):
    try:
        value = json.loads(raw_paper.source_ref_json or "{}")
    except (TypeError, ValueError):
        value = {}
    return value if isinstance(value, dict) else {}


def _normalize_sciencedirect_pii(value):
    pii = str(value or "").strip()
    if _COMPACT_PII_RE.fullmatch(pii):
        return pii.upper()
    if _LEGACY_PII_RE.fullmatch(pii):
        return re.sub(r"[-()]", "", pii).upper()
    return ""


def resolve_fulltext_reference(raw_paper):
    """返回当前原始论文可用的全文提供器引用，无法识别时返回 None。"""
    refs = _source_refs(raw_paper)
    detail_url = str(raw_paper.detail_url or "").strip()
    source_type = getattr(getattr(raw_paper, "raw_issue", None), "source_type", "")

    article_id = refs.get("article_id")
    if not article_id and source_type == "magtech":
        match = _MAGTECH_ARTICLE_RE.search(detail_url)
        article_id = match.group(1) if match else None
    if source_type == "magtech" and article_id:
        return FullTextReference(
            provider_id="magtech",
            paper_ref={"article_id": str(article_id)},
            action_url=detail_url or None,
        )

    pii = str(refs.get("pii") or "").strip()
    parsed = urlparse(detail_url)
    is_sciencedirect = parsed.hostname in {"sciencedirect.com", "www.sciencedirect.com"}
    if not pii and is_sciencedirect:
        match = _SCIENCEDIRECT_PII_RE.search(parsed.path)
        pii = match.group(1) if match else ""
    pii = _normalize_sciencedirect_pii(pii)
    if pii:
        article_url = f"https://www.sciencedirect.com/science/article/pii/{pii}"
        paper_ref = {"pii": pii}
        doi = str(refs.get("doi") or raw_paper.doi or "").strip()
        if doi:
            paper_ref["doi"] = doi
        return FullTextReference(
            provider_id="sciencedirect",
            paper_ref=paper_ref,
            action_url=article_url,
        )
    return None


def build_fulltext_provider(provider_id, journal_name):
    """构造一个全文提供器；题录源配置仅在对应提供器需要时读取。"""
    if provider_id == "magtech":
        from app.collection.services.ingestion_service import load_source_config
        from app.collection.sources.registry import get_source

        return get_source("magtech", load_source_config(journal_name, "magtech"))
    if provider_id == "sciencedirect":
        from app.collection.fulltext.sciencedirect import ScienceDirectFullTextProvider

        return ScienceDirectFullTextProvider()
    raise ValueError(f"不支持的全文提供器：{provider_id}")
