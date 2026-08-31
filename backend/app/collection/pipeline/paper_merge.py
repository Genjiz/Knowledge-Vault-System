"""采集入库打通（T-4）：raw_paper → 统一论文表 upsert。

本模块属于 collection 侧，负责把采集原始模型映射为论文数据，
再委托 papers/services/paper_service.py 落库——papers 不感知采集模型。
"""
from app.papers.services.paper_service import keywords_to_text, PaperService


class PaperMergeService:
    def __init__(self, paper_service=None):
        self.paper_service = paper_service or PaperService()

    def upsert_raw_paper(self, raw_paper):
        raw_issue = raw_paper.raw_issue
        language = "zh" if (raw_issue.source_type or "").lower() == "domestic" else "en"

        return self.paper_service.upsert_literature(
            {
                "title": (raw_paper.title or "").strip(),
                "authors": raw_paper.authors or "",
                "journal": raw_issue.journal_name,
                "year": raw_issue.year,
                "issue": raw_issue.issue,
                "abstract": raw_paper.abstract,
                "pages": raw_paper.pages,
                "url": raw_paper.detail_url,
                "language": language,
                "source": "collection",
                "source_raw_paper_id": raw_paper.id,
                "keywords": keywords_to_text(raw_paper.keywords_json),
            }
        )

    def sync_issue(self, raw_issue):
        """把某期号下的全部原始论文合并入库，返回论文列表。"""
        return [self.upsert_raw_paper(paper) for paper in raw_issue.papers]
