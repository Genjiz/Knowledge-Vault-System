"""期刊与采集源的初始数据播种。

「当前支持哪些期刊」此前散落在 legacy 缓存文件里（NCPSSD 的 journal_url_cache.json），
播种把它们搬进 journal / journal_source_config，之后由「期刊与采集源」页面维护。

播种只补不覆盖：已存在的期刊与其源配置不会被重置，避免抹掉页面上的手工调整。
"""
import json
from pathlib import Path

from app.collection.runtime.paths import get_legacy_crawler_root
from app.core.extensions import db
from app.papers.models import Journal, JournalSourceConfig

NCPSSD_CACHE_NAME = "journal_url_cache.json"

# 已知 Magtech 官网地址。官网源不依赖浏览器、稳定性优于 NCPSSD，播种时设为默认源。
MAGTECH_SITES = {
    "情报学报": "https://qbxb.istic.ac.cn",
}

# Elsevier 源的示例期刊；slug 必须与 legacy/foreign/config_foreign.py 的 JOURNAL_SLUGS 键一致
ELSEVIER_JOURNALS = ("Information Processing & Management",)


def ncpssd_journal_names():
    """NCPSSD 已收录的期刊名，取自 legacy 抓取脚本维护的缓存。"""
    cache_path = Path(get_legacy_crawler_root()) / "domestic" / NCPSSD_CACHE_NAME
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return sorted(cache)


def _known_entries():
    """内置清单：期刊名 / 区域 / 源配置 / 是否默认源。

    NCPSSD 收录的为国内期刊；Magtech 官网源只服务国内期刊；Elsevier 源为国外期刊。
    """
    entries = [(name, "domestic", "ncpssd", None, False) for name in ncpssd_journal_names()]
    entries += [
        (name, "domestic", "magtech", {"base_url": base_url}, True)
        for name, base_url in MAGTECH_SITES.items()
    ]
    entries += [(name, "foreign", "elsevier", None, True) for name in ELSEVIER_JOURNALS]
    return entries


def seed_known_journals():
    """补齐内置期刊与可用源配置，返回本次新建与补配的期刊名。"""
    created, updated = [], []
    touched = set()

    for name, region, source_id, config, mark_default in _known_entries():
        journal = Journal.query.filter_by(name=name).first()
        if journal is None:
            journal = Journal(name=name, region=region)
            db.session.add(journal)
            db.session.flush()
            created.append(name)
        elif not journal.region:
            journal.region = region
        touched.add(journal.id)

        row = JournalSourceConfig.query.filter_by(journal_id=journal.id, source_id=source_id).first()
        if row is None:
            row = JournalSourceConfig(journal_id=journal.id, source_id=source_id, enabled=True)
            db.session.add(row)
            if name not in created:
                updated.append(name)
        if config and not row.config_json:
            row.config_json = json.dumps(config, ensure_ascii=False)
        if mark_default:
            row.is_default = True

    for journal_id in touched:
        _ensure_single_default(journal_id)

    db.session.commit()
    return {"created": created, "updated": sorted(set(updated))}


def _ensure_single_default(journal_id):
    """同一期刊至多一个默认源：已有默认则保留，否则取排序最前的已启用源。"""
    rows = (
        JournalSourceConfig.query.filter_by(journal_id=journal_id)
        .order_by(JournalSourceConfig.source_id)
        .all()
    )
    enabled = [row for row in rows if row.enabled]
    if not enabled:
        return

    default = next((row for row in enabled if row.is_default), enabled[0])
    for row in rows:
        row.is_default = row is default
