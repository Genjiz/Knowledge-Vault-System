"""论文域服务：统一论文实体的落库与合并（采集与手动导入共用的入口）。

只接收纯 dict 数据，不感知采集模型——raw → dict 的映射在 collection/pipeline 完成。
"""
import json

from app.core.extensions import db
from app.papers.models import Journal, Literature


def normalize_title(title):
    """题录去重键：去除首尾空白、压缩内部空白、忽略大小写。"""
    return " ".join(str(title or "").split()).casefold()


def keywords_to_text(keywords_json):
    if not keywords_json:
        return None
    try:
        parsed = json.loads(keywords_json)
        if isinstance(parsed, list):
            return ", ".join(str(k) for k in parsed)
    except (ValueError, TypeError):
        pass
    return keywords_json


class PaperService:
    def get_or_create_journal(self, name):
        if not name:
            return None
        name = str(name).strip()
        journal = Journal.query.filter_by(name=name).first()
        if journal is None:
            journal = Journal(name=name)
            db.session.add(journal)
            db.session.flush()
        return journal

    def find_by_title(self, title):
        normalized = normalize_title(title)
        if not normalized:
            return None
        candidates = Literature.query.all()
        for candidate in candidates:
            if normalize_title(candidate.title) == normalized:
                return candidate
        return None

    def upsert_literature(self, data):
        """按标题去重合并：已存在则只填充空字段（不覆盖用户数据），不存在则创建。"""
        literature = self.find_by_title(data.get("title"))
        if literature is None:
            literature = Literature(title=data.get("title"), authors=data.get("authors") or "")
            db.session.add(literature)

        for field, value in data.items():
            if field in ("title", "journal", "journal_id"):
                continue
            current = getattr(literature, field, None)
            if current in (None, "") and value not in (None, ""):
                setattr(literature, field, value)

        journal_id = data.get("journal_id")
        if journal_id:
            literature.journal_id = journal_id
        elif data.get("journal") and not literature.journal_id:
            journal = self.get_or_create_journal(data.get("journal"))
            literature.journal_id = journal.id

        # journal 字符串字段为历史字段（前端列表依赖），与 journal_id 保持一致
        if data.get("journal") and not literature.journal:
            literature.journal = data.get("journal")

        db.session.commit()
        return literature
