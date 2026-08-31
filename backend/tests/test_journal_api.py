import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class JournalApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def test_list_journals_returns_empty_list(self):
        response = self.client.get("/api/journals")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], [])

    def test_create_journal(self):
        response = self.client.post(
            "/api/journals",
            json={"name": "情报学报", "issn": "1000-0135"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["name"], "情报学报")
        self.assertEqual(payload["issn"], "1000-0135")
        self.assertEqual(payload["sources"], [])

    def test_create_journal_rejects_missing_name(self):
        response = self.client.post("/api/journals", json={"issn": "1000-0135"})

        self.assertEqual(response.status_code, 400)

    def test_create_journal_rejects_duplicate_name(self):
        self.client.post("/api/journals", json={"name": "情报学报"})
        response = self.client.post("/api/journals", json={"name": "情报学报"})

        self.assertEqual(response.status_code, 409)

    def test_update_journal_source_config(self):
        create_response = self.client.post("/api/journals", json={"name": "情报学报"})
        journal_id = create_response.get_json()["data"]["id"]

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"source_id": "ncpssd", "enabled": True},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["source_id"], "ncpssd")
        self.assertTrue(payload["enabled"])

        list_response = self.client.get("/api/journals")
        journals = list_response.get_json()["data"]
        self.assertEqual(len(journals[0]["sources"]), 1)
        self.assertEqual(journals[0]["sources"][0]["source_id"], "ncpssd")

    def test_update_journal_source_rejects_unknown_source(self):
        create_response = self.client.post("/api/journals", json={"name": "情报学报"})
        journal_id = create_response.get_json()["data"]["id"]

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"source_id": "not-a-source"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
