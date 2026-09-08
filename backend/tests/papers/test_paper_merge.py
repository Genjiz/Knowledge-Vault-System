import sys
import json
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class PaperMergeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def _make_raw_paper(self, title="Deep Learning for IR", authors="Alice, Bob", abstract="An abstract"):
        from app.collection.models import RawIssue, RawPaper

        raw_issue = RawIssue(
            source_type="foreign",
            journal_name="Journal of Information Science",
            year=2025,
            issue="3",
            paper_count=1,
        )
        db.session.add(raw_issue)
        db.session.flush()
        raw_paper = RawPaper(
            raw_issue_id=raw_issue.id,
            title=title,
            authors=authors,
            abstract=abstract,
            pages="1-10",
            detail_url="https://example.com/paper",
        )
        db.session.add(raw_paper)
        db.session.commit()
        return raw_issue, raw_paper

    def _make_source_raw_paper(
        self,
        source_type,
        title="跨来源论文",
        authors="作者",
        abstract=None,
        doi="10.1000/multi-source",
    ):
        from app.collection.models import RawIssue, RawPaper

        raw_issue = RawIssue(
            source_type=source_type,
            region="domestic",
            journal_name="情报学报",
            year=2026,
            issue="3",
            paper_count=1,
        )
        db.session.add(raw_issue)
        db.session.flush()
        raw_paper = RawPaper(
            raw_issue_id=raw_issue.id,
            title=title,
            authors=authors,
            abstract=abstract,
            doi=doi,
        )
        db.session.add(raw_paper)
        db.session.commit()
        return raw_issue, raw_paper

    def test_upsert_creates_paper_with_provenance(self):
        from app.papers.models import Journal, Literature
        from app.collection.pipeline.paper_merge import PaperMergeService

        raw_issue, raw_paper = self._make_raw_paper()

        literature = PaperMergeService().upsert_raw_paper(raw_paper)

        self.assertEqual(literature.title, "Deep Learning for IR")
        self.assertEqual(literature.source, "collection")
        self.assertEqual(literature.source_raw_paper_id, raw_paper.id)
        self.assertEqual(literature.journal, "Journal of Information Science")
        self.assertIsNotNone(literature.journal_id)
        self.assertEqual(
            db.session.get(Journal, literature.journal_id).name,
            "Journal of Information Science",
        )
        self.assertEqual(literature.year, 2025)
        self.assertEqual(literature.abstract, "An abstract")
        self.assertEqual(literature.language, "en")

    def test_upsert_domestic_paper_marks_chinese_language(self):
        from app.collection.pipeline.paper_merge import PaperMergeService

        raw_issue, raw_paper = self._make_raw_paper(title="情报学研究进展", abstract="摘要")
        raw_issue.source_type = "ncpssd"
        raw_issue.region = "domestic"
        db.session.commit()

        literature = PaperMergeService().upsert_raw_paper(raw_paper)
        self.assertEqual(literature.language, "zh")

    def test_upsert_fills_existing_paper_without_overwrite(self):
        from app.papers.models import Literature
        from app.collection.pipeline.paper_merge import PaperMergeService

        existing = Literature(
            title="Deep Learning for IR",
            authors="",
            journal="Journal of Information Science",
            year=2025,
            issue="3",
            status="已读",
            abstract=None,
        ).save()
        _, raw_paper = self._make_raw_paper()

        literature = PaperMergeService().upsert_raw_paper(raw_paper)

        self.assertEqual(literature.id, existing.id)
        self.assertEqual(literature.status, "已读")
        self.assertEqual(literature.abstract, "An abstract")
        self.assertEqual(literature.authors, "Alice, Bob")
        self.assertEqual(db.session.query(Literature).count(), 1)

    def test_upsert_is_idempotent(self):
        from app.papers.models import Literature
        from app.collection.pipeline.paper_merge import PaperMergeService

        _, raw_paper = self._make_raw_paper()
        service = PaperMergeService()

        first = service.upsert_raw_paper(raw_paper)
        second = service.upsert_raw_paper(raw_paper)

        self.assertEqual(first.id, second.id)
        self.assertEqual(db.session.query(Literature).count(), 1)

    def test_upsert_matching_is_case_and_whitespace_insensitive(self):
        from app.papers.models import Literature
        from app.collection.pipeline.paper_merge import PaperMergeService

        Literature(
            title="  deep learning for IR  ",
            authors="Someone",
            journal="Journal of Information Science",
            year=2025,
            issue="3",
        ).save()
        _, raw_paper = self._make_raw_paper(title="Deep Learning for IR")

        literature = PaperMergeService().upsert_raw_paper(raw_paper)

        self.assertEqual(db.session.query(Literature).count(), 1)
        self.assertEqual(literature.title.strip().lower(), "deep learning for ir")

    def test_multi_source_uses_priority_and_keeps_all_provenance(self):
        from app.collection.models import LiteratureSource
        from app.collection.pipeline.paper_merge import PaperMergeService

        _, ncpssd = self._make_source_raw_paper(
            "ncpssd", authors="聚合平台作者[1]", abstract=None
        )
        _, magtech = self._make_source_raw_paper(
            "magtech", authors="官网作者", abstract="官网摘要"
        )
        service = PaperMergeService()

        first = service.upsert_raw_paper(ncpssd)
        second = service.upsert_raw_paper(magtech)

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.authors, "官网作者")
        self.assertEqual(second.abstract, "官网摘要")
        self.assertEqual(second.source_raw_paper_id, magtech.id)
        self.assertEqual(json.loads(second.field_sources_json)["authors"], "magtech")
        self.assertEqual(json.loads(second.field_sources_json)["abstract"], "magtech")
        self.assertEqual(
            LiteratureSource.query.filter_by(literature_id=second.id).count(),
            2,
        )

    def test_paired_markup_does_not_create_cross_source_duplicate(self):
        from app.papers.models import Literature
        from app.collection.pipeline.paper_merge import PaperMergeService

        _, ncpssd = self._make_source_raw_paper(
            "ncpssd", title="基于XGBoost的方法", doi=None
        )
        _, magtech = self._make_source_raw_paper(
            "magtech", title="基于<bold>XGBoost</bold>的方法", doi=None
        )
        service = PaperMergeService()

        service.upsert_raw_paper(ncpssd)
        literature = service.upsert_raw_paper(magtech)

        self.assertEqual(Literature.query.count(), 1)
        self.assertEqual(literature.title, "基于XGBoost的方法")

    def test_same_title_without_doi_requires_matching_issue_context(self):
        from app.collection.pipeline.paper_merge import PaperMergeService
        from app.papers.models import Literature

        _, first = self._make_source_raw_paper(
            "ncpssd", title="同名论文", doi=None
        )
        _, second = self._make_source_raw_paper(
            "magtech", title="同名论文", doi=None
        )
        second.raw_issue.journal_name = "另一种期刊"
        db.session.commit()

        service = PaperMergeService()
        service.upsert_raw_paper(first)
        service.upsert_raw_paper(second)

        self.assertEqual(Literature.query.count(), 2)

    def test_user_edited_fields_are_not_overwritten_by_higher_priority_source(self):
        from app.collection.pipeline.paper_merge import PaperMergeService

        _, ncpssd = self._make_source_raw_paper("ncpssd", authors="平台作者")
        _, magtech = self._make_source_raw_paper("magtech", authors="官网作者")
        service = PaperMergeService()
        literature = service.upsert_raw_paper(ncpssd)
        literature.authors = "用户修订作者"
        literature.user_edited_fields_json = json.dumps(["authors"], ensure_ascii=False)
        db.session.commit()

        literature = service.upsert_raw_paper(magtech)

        self.assertEqual(literature.authors, "用户修订作者")
        self.assertEqual(json.loads(literature.field_sources_json)["authors"], "user")

    def test_deleting_higher_priority_issue_falls_back_to_remaining_source(self):
        from app.collection.models import LiteratureSource, RawIssue
        from app.collection.pipeline.paper_merge import PaperMergeService
        from app.collection.services.raw_issue_service import RawIssueService

        _, ncpssd = self._make_source_raw_paper(
            "ncpssd", authors="平台作者", abstract="平台摘要"
        )
        magtech_issue, magtech = self._make_source_raw_paper(
            "magtech", authors="官网作者", abstract="官网摘要"
        )
        service = PaperMergeService()
        literature = service.upsert_raw_paper(ncpssd)
        literature = service.upsert_raw_paper(magtech)

        RawIssueService().delete_issue(magtech_issue.id)
        db.session.refresh(literature)

        self.assertIsNone(db.session.get(RawIssue, magtech_issue.id))
        self.assertEqual(literature.authors, "平台作者")
        self.assertEqual(literature.abstract, "平台摘要")
        self.assertEqual(json.loads(literature.field_sources_json)["authors"], "ncpssd")
        self.assertEqual(
            LiteratureSource.query.filter_by(literature_id=literature.id).count(),
            1,
        )

    def test_deleting_last_source_preserves_materialized_literature(self):
        from app.collection.models import LiteratureSource
        from app.collection.pipeline.paper_merge import PaperMergeService
        from app.collection.services.raw_issue_service import RawIssueService
        from app.papers.models import Literature

        issue, raw_paper = self._make_source_raw_paper(
            "magtech", authors="官网作者", abstract="官网摘要"
        )
        literature = PaperMergeService().upsert_raw_paper(raw_paper)

        RawIssueService().delete_issue(issue.id)
        preserved = db.session.get(Literature, literature.id)

        self.assertIsNotNone(preserved)
        self.assertEqual(preserved.title, "跨来源论文")
        self.assertEqual(preserved.abstract, "官网摘要")
        self.assertEqual(
            LiteratureSource.query.filter_by(literature_id=literature.id).count(),
            0,
        )
        self.assertIsNone(preserved.source_raw_paper_id)
        self.assertEqual(json.loads(preserved.field_sources_json)["abstract"], "retained")


if __name__ == "__main__":
    unittest.main()
