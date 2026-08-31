import sys
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


if __name__ == "__main__":
    unittest.main()
