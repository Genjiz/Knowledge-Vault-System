import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class FakePdfSource:
    def __init__(self, payload=b"%PDF-1.4\nfixture"):
        self.payload = payload
        self.calls = []

    def download_pdf(self, paper_ref, **kwargs):
        from app.collection.sources.base import PdfDownload

        self.calls.append(paper_ref)
        if isinstance(self.payload, Exception):
            raise self.payload
        return PdfDownload(
            content=self.payload,
            source_url="https://example.com/article.pdf",
            content_type="application/x-download",
        )


class FullTextServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "fulltext"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True)
        self.app.config["UPLOAD_FOLDER"] = str(self.temp_dir / "uploads" / "pdfs")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _seed_paper(self, title="官网论文", article_id="1044", pdf_path=None, pdf_source=None):
        from app.collection.models import LiteratureSource, RawIssue, RawPaper
        from app.papers.models import Literature

        issue = RawIssue(
            source_type="magtech",
            region="domestic",
            journal_name="情报学报",
            year=2026,
            issue="7",
            paper_count=1,
        )
        db.session.add(issue)
        db.session.flush()
        raw_paper = RawPaper(
            raw_issue_id=issue.id,
            source_identifier=f"10.1000/{article_id}",
            source_ref_json=json.dumps({"article_id": article_id}),
            title=title,
            authors="作者",
            detail_url=f"https://example.com/CN/abstract/article_{article_id}.shtml",
        )
        literature = Literature(
            title=title,
            authors="作者",
            source="collection",
            pdf_path=pdf_path,
            pdf_source_type=pdf_source,
        )
        db.session.add_all([raw_paper, literature])
        db.session.flush()
        db.session.add(
            LiteratureSource(
                literature_id=literature.id,
                raw_paper_id=raw_paper.id,
                source_type="magtech",
            )
        )
        db.session.commit()
        return issue, raw_paper, literature

    def test_single_task_downloads_valid_pdf_and_records_provenance(self):
        from app.collection.services.fulltext_service import FullTextService

        _, raw_paper, literature = self._seed_paper()
        source = FakePdfSource()
        service = FullTextService(source_factory=lambda *_: source)

        task = service.create_single_task(literature.id)
        service.run_task(task.id)
        db.session.refresh(literature)
        db.session.refresh(task)

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.succeeded_count, 1)
        self.assertEqual(literature.pdf_source_type, "magtech")
        self.assertEqual(literature.pdf_source_raw_paper_id, raw_paper.id)
        self.assertEqual(literature.pdf_size_bytes, len(source.payload))
        pdf_path = self.temp_dir / literature.pdf_path
        self.assertEqual(pdf_path.read_bytes(), source.payload)
        self.assertFalse(list(pdf_path.parent.glob("*.part-*")))

    def test_issue_task_skips_existing_user_pdf_and_downloads_missing_pdf(self):
        from app.collection.models import LiteratureSource, RawPaper
        from app.collection.services.fulltext_service import FullTextService
        from app.papers.models import Literature

        issue, _, protected = self._seed_paper(
            title="用户文件论文",
            article_id="1044",
            pdf_path="uploads/pdfs/protected.pdf",
            pdf_source="user",
        )
        second_raw = RawPaper(
            raw_issue_id=issue.id,
            source_identifier="10.1000/1045",
            source_ref_json=json.dumps({"article_id": "1045"}),
            title="待下载论文",
            authors="作者",
        )
        second_literature = Literature(title="待下载论文", authors="作者", source="collection")
        db.session.add_all([second_raw, second_literature])
        db.session.flush()
        db.session.add(
            LiteratureSource(
                literature_id=second_literature.id,
                raw_paper_id=second_raw.id,
                source_type="magtech",
            )
        )
        issue.paper_count = 2
        db.session.commit()
        source = FakePdfSource()
        service = FullTextService(source_factory=lambda *_: source)

        task = service.create_issue_task(issue.id)
        service.run_task(task.id)
        db.session.refresh(task)
        db.session.refresh(protected)
        db.session.refresh(second_literature)

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.succeeded_count, 1)
        self.assertEqual(task.skipped_count, 1)
        self.assertEqual(protected.pdf_path, "uploads/pdfs/protected.pdf")
        self.assertEqual(protected.pdf_source_type, "user")
        self.assertEqual(second_literature.pdf_source_type, "magtech")
        self.assertEqual(source.calls, [{"article_id": "1045"}])

    def test_invalid_download_fails_without_attaching_file(self):
        from app.collection.services.fulltext_service import FullTextService

        _, _, literature = self._seed_paper()
        service = FullTextService(source_factory=lambda *_: FakePdfSource(b"<html>login</html>"))

        task = service.create_single_task(literature.id)
        service.run_task(task.id)
        db.session.refresh(task)
        db.session.refresh(literature)

        self.assertEqual(task.status, "failed")
        self.assertEqual(task.failed_count, 1)
        self.assertIsNone(literature.pdf_path)
        self.assertEqual(list((self.temp_dir / "uploads" / "pdfs").glob("*")), [])

    def test_issue_task_records_partial_status_when_only_some_downloads_succeed(self):
        from app.collection.models import LiteratureSource, RawPaper
        from app.collection.services.fulltext_service import FullTextService
        from app.collection.sources.base import PdfDownload, ProviderError
        from app.papers.models import Literature

        issue, _, _ = self._seed_paper(article_id="1044")
        second_raw = RawPaper(
            raw_issue_id=issue.id,
            source_identifier="10.1000/1045",
            source_ref_json=json.dumps({"article_id": "1045"}),
            title="下载失败论文",
            authors="作者",
        )
        second_literature = Literature(title="下载失败论文", authors="作者", source="collection")
        db.session.add_all([second_raw, second_literature])
        db.session.flush()
        db.session.add(
            LiteratureSource(
                literature_id=second_literature.id,
                raw_paper_id=second_raw.id,
                source_type="magtech",
            )
        )
        db.session.commit()

        class PartialSource:
            def download_pdf(self, paper_ref, **kwargs):
                if paper_ref["article_id"] == "1045":
                    raise ProviderError("官网暂时不可用")
                return PdfDownload(
                    content=b"%PDF-1.4\nfixture",
                    source_url="https://example.com/1044.pdf",
                )

        service = FullTextService(source_factory=lambda *_: PartialSource())
        task = service.create_issue_task(issue.id)
        service.run_task(task.id)
        db.session.refresh(task)

        self.assertEqual(task.status, "partial")
        self.assertEqual(task.total_count, 2)
        self.assertEqual(task.succeeded_count, 1)
        self.assertEqual(task.failed_count, 1)
        self.assertEqual(task.skipped_count, 0)

    def test_single_task_can_replace_existing_magtech_pdf(self):
        from app.collection.services.fulltext_service import FullTextService

        _, raw_paper, literature = self._seed_paper(
            pdf_path="uploads/pdfs/old.pdf",
            pdf_source="magtech",
        )
        literature.pdf_source_raw_paper_id = raw_paper.id
        db.session.commit()
        source = FakePdfSource(b"%PDF-1.4\nreplacement")
        service = FullTextService(source_factory=lambda *_: source)

        task = service.create_single_task(literature.id, replace_existing=True)
        service.run_task(task.id)
        db.session.refresh(literature)

        self.assertEqual(task.status, "completed")
        self.assertEqual((self.temp_dir / literature.pdf_path).read_bytes(), source.payload)
        self.assertEqual(literature.pdf_source_type, "magtech")
        self.assertEqual(literature.pdf_source_raw_paper_id, raw_paper.id)

    def test_single_task_cannot_replace_pdf_from_another_automatic_source(self):
        from app.collection.services.fulltext_service import (
            FullTextConflictError,
            FullTextService,
        )

        _, _, literature = self._seed_paper(
            pdf_path="uploads/pdfs/other.pdf",
            pdf_source="other-provider",
        )

        with self.assertRaises(FullTextConflictError):
            FullTextService().create_single_task(literature.id, replace_existing=True)

    def test_deleting_issue_preserves_downloaded_pdf_and_task_history(self):
        from app.collection.services.fulltext_service import FullTextService
        from app.collection.services.raw_issue_service import RawIssueService

        issue, _, literature = self._seed_paper()
        service = FullTextService(source_factory=lambda *_: FakePdfSource())
        task = service.create_single_task(literature.id)
        service.run_task(task.id)

        RawIssueService().delete_issue(issue.id)
        db.session.refresh(literature)
        db.session.refresh(task)

        self.assertTrue((self.temp_dir / literature.pdf_path).is_file())
        self.assertEqual(literature.pdf_source_type, "magtech")
        self.assertIsNone(literature.pdf_source_raw_paper_id)
        self.assertIsNone(task.items[0].raw_paper_id)


if __name__ == "__main__":
    unittest.main()
