import sys
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class LiteratureJournalFilterTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "literature-api"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.app.config["UPLOAD_FOLDER"] = str(self.temp_dir / "uploads" / "pdfs")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        from app.papers.models import Journal, Literature

        self.journal_a = Journal(name="情报学报").save()
        self.journal_b = Journal(name="JASIST").save()
        Literature(title="论文A", authors="张三", journal_id=self.journal_a.id).save()
        Literature(title="论文B", authors="李四", journal_id=self.journal_b.id).save()
        Literature(title="论文C", authors="王五").save()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_filter_by_journal_id(self):
        response = self.client.get(f"/api/literatures?journal_id={self.journal_a.id}")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        titles = [item["title"] for item in payload["items"]]
        self.assertEqual(titles, ["论文A"])

    def test_filter_without_journal_id_returns_all(self):
        response = self.client.get("/api/literatures")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["total"], 3)

    def test_create_and_update_track_explicit_user_fields(self):
        response = self.client.post(
            "/api/literatures",
            json={"title": "用户论文", "authors": "用户作者", "abstract": ""},
        )
        self.assertEqual(response.status_code, 200)
        created = response.get_json()["data"]
        self.assertEqual(
            set(json.loads(created["user_edited_fields_json"])),
            {"authors", "title"},
        )

        updated = self.client.put(
            f"/api/literatures/{created['id']}",
            json={
                "abstract": "",
                "authors": "修订作者",
                "user_edited_fields": ["authors"],
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            set(json.loads(updated.get_json()["data"]["user_edited_fields_json"])),
            {"authors", "title"},
        )

        cleared = self.client.put(
            f"/api/literatures/{created['id']}",
            json={"abstract": "", "user_edited_fields": ["abstract"]},
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(
            set(json.loads(cleared.get_json()["data"]["user_edited_fields_json"])),
            {"abstract", "authors", "title"},
        )

    def test_manual_pdf_upload_and_delete_update_pdf_provenance(self):
        from app.papers.models import Literature

        literature = Literature(title="PDF 论文", authors="作者").save()
        content = b"%PDF-1.4\nmanual"

        uploaded = self.client.post(
            f"/api/literatures/{literature.id}/pdf",
            data={"file": (io.BytesIO(content), "manual.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(uploaded.status_code, 200)
        db.session.refresh(literature)
        self.assertEqual(literature.pdf_source_type, "user")
        self.assertEqual(literature.pdf_sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(literature.pdf_size_bytes, len(content))

        deleted = self.client.delete(f"/api/literatures/{literature.id}/pdf")

        self.assertEqual(deleted.status_code, 200)
        db.session.refresh(literature)
        self.assertIsNone(literature.pdf_path)
        self.assertIsNone(literature.pdf_source_type)
        self.assertIsNone(literature.pdf_sha256)


if __name__ == "__main__":
    unittest.main()
