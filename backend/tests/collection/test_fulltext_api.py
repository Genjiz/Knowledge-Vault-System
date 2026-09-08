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


class FullTextApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "fulltext-api"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True)
        self.app.config["UPLOAD_FOLDER"] = str(self.temp_dir / "uploads" / "pdfs")
        self.scheduled = []
        self.app.config["FULLTEXT_TASK_EXECUTOR"] = self.scheduled.append
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _seed(self, source_type="magtech", pdf_path=None, pdf_source=None):
        from app.collection.models import LiteratureSource, RawIssue, RawPaper
        from app.papers.models import Literature

        issue = RawIssue(
            source_type=source_type,
            region="domestic",
            journal_name="情报学报",
            year=2026,
            issue="7",
            paper_count=1,
        )
        db.session.add(issue)
        db.session.flush()
        raw = RawPaper(
            raw_issue_id=issue.id,
            source_ref_json=json.dumps({"article_id": "1044"}),
            title="测试论文",
            authors="作者",
        )
        literature = Literature(
            title="测试论文",
            authors="作者",
            source="collection",
            pdf_path=pdf_path,
            pdf_source_type=pdf_source,
        )
        db.session.add_all([raw, literature])
        db.session.flush()
        db.session.add(
            LiteratureSource(
                literature_id=literature.id,
                raw_paper_id=raw.id,
                source_type=source_type,
            )
        )
        db.session.commit()
        return issue, literature

    def test_single_and_issue_endpoints_create_pollable_tasks(self):
        issue, literature = self._seed()

        single = self.client.post(f"/api/literatures/{literature.id}/fulltext-tasks")
        self.assertEqual(single.status_code, 200)
        single_task = single.get_json()["data"]
        self.assertEqual(single_task["mode"], "single")
        self.assertEqual(self.scheduled, [single_task["id"]])

        detail = self.client.get(f"/api/fulltext-tasks/{single_task['id']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.get_json()["data"]["items"]), 1)

        batch = self.client.post(f"/api/raw-issues/{issue.id}/fulltext-tasks")
        self.assertEqual(batch.status_code, 200)
        self.assertEqual(batch.get_json()["data"]["mode"], "issue")

    def test_user_uploaded_pdf_cannot_be_replaced_by_online_task(self):
        _, literature = self._seed(
            pdf_path="uploads/pdfs/manual.pdf",
            pdf_source="user",
        )

        response = self.client.post(
            f"/api/literatures/{literature.id}/fulltext-tasks",
            json={"replace_existing": True},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("用户上传", response.get_json()["message"])

    def test_repeated_request_returns_active_task_without_scheduling_it_twice(self):
        _, literature = self._seed()

        first = self.client.post(f"/api/literatures/{literature.id}/fulltext-tasks")
        second = self.client.post(f"/api/literatures/{literature.id}/fulltext-tasks")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.get_json()["data"]["id"], second.get_json()["data"]["id"])
        self.assertEqual(self.scheduled, [first.get_json()["data"]["id"]])

    def test_non_magtech_issue_is_not_supported(self):
        issue, _ = self._seed(source_type="ncpssd")

        response = self.client.post(f"/api/raw-issues/{issue.id}/fulltext-tasks")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Magtech", response.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
