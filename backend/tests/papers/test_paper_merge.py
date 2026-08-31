import sys
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
        raw_issue.source_type = "domestic"
        db.session.commit()

        literature = PaperMergeService().upsert_raw_paper(raw_paper)
        self.assertEqual(literature.language, "zh")

    def test_upsert_fills_existing_paper_without_overwrite(self):
        from app.papers.models import Literature
        from app.collection.pipeline.paper_merge import PaperMergeService

        existing = Literature(
            title="Deep Learning for IR",
            authors="",
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

        Literature(title="  deep learning for IR  ", authors="Someone").save()
        _, raw_paper = self._make_raw_paper(title="Deep Learning for IR")

        literature = PaperMergeService().upsert_raw_paper(raw_paper)

        self.assertEqual(db.session.query(Literature).count(), 1)
        self.assertEqual(literature.title.strip().lower(), "deep learning for ir")


if __name__ == "__main__":
    unittest.main()
