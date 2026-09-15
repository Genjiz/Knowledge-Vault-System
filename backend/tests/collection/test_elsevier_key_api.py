import os
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


class ElsevierKeyApiTestCase(unittest.TestCase):
    def setUp(self):
        self.original = os.environ.pop("ELSEVIER_API_KEY", None)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.app = create_app("testing")
        self.app.config["COLLECTION_ENV_PATH"] = str(self.env_path)
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ.pop("ELSEVIER_API_KEY", None)
        if self.original is not None:
            os.environ["ELSEVIER_API_KEY"] = self.original
        self.temp_dir.cleanup()

    def test_get_put_and_clear_never_return_plaintext(self):
        self.assertEqual(
            self.client.get("/api/collection/elsevier-key").get_json()["data"],
            {"has_api_key": False},
        )

        response = self.client.put(
            "/api/collection/elsevier-key", json={"api_key": "test-secret-key"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], {"has_api_key": True})
        self.assertNotIn("test-secret-key", response.get_data(as_text=True))
        self.assertEqual(os.environ["ELSEVIER_API_KEY"], "test-secret-key")

        response = self.client.put("/api/collection/elsevier-key", json={"clear": True})
        self.assertEqual(response.get_json()["data"], {"has_api_key": False})
        self.assertNotIn("ELSEVIER_API_KEY", os.environ)

    def test_put_rejects_empty_key_without_clear(self):
        response = self.client.put(
            "/api/collection/elsevier-key", json={"api_key": "   "}
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
