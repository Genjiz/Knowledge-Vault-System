import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class FakeSecretStore:
    def __init__(self):
        self.values = {}

    def get(self, profile_key):
        return self.values.get(str(profile_key))

    def set(self, profile_key, api_key):
        self.values[str(profile_key)] = api_key

    def delete(self, profile_key):
        self.values.pop(str(profile_key), None)


class FakeAdapter:
    def __init__(self, profile, api_key):
        self.profile = profile
        self.api_key = api_key

    def generate_text(self, prompt):
        return f"{self.profile.model_name}:{prompt}"


class LLMPlatformApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.secrets = FakeSecretStore()
        self.app.config["LLM_SECRET_STORE"] = self.secrets
        self.app.config["LLM_ADAPTER_FACTORY"] = lambda profile, key: FakeAdapter(profile, key)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def test_profile_crud_never_returns_api_key(self):
        response = self.client.post(
            "/api/llm/profiles",
            json={
                "name": "Local Model",
                "protocol": "openai",
                "base_url": "http://127.0.0.1:11434/v1",
                "model_name": "qwen-test",
                "api_key": "top-secret",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = response.get_json()["data"]
        self.assertTrue(profile["has_api_key"])
        self.assertNotIn("api_key", profile)
        self.assertNotIn("top-secret", response.get_data(as_text=True))
        self.assertEqual(self.secrets.get(profile["id"]), "top-secret")

        listed = self.client.get("/api/llm/profiles").get_json()["data"]
        self.assertEqual(len(listed), 1)
        self.assertNotIn("api_key", listed[0])

        updated = self.client.put(
            f"/api/llm/profiles/{profile['id']}",
            json={"model_name": "qwen-new", "api_key": ""},
        ).get_json()["data"]
        self.assertEqual(updated["model_name"], "qwen-new")
        self.assertEqual(self.secrets.get(profile["id"]), "top-secret")

    def test_scene_binding_drives_generation_and_allows_override(self):
        from app.core.llm.service import LLMService

        first = self.client.post(
            "/api/llm/profiles",
            json={
                "name": "First",
                "protocol": "gemini",
                "model_name": "gemini-test",
                "api_key": "key-1",
            },
        ).get_json()["data"]
        second = self.client.post(
            "/api/llm/profiles",
            json={
                "name": "Second",
                "protocol": "openai",
                "base_url": "https://example.invalid/v1",
                "model_name": "openai-test",
                "api_key": "key-2",
            },
        ).get_json()["data"]

        bound = self.client.put(
            "/api/llm/scenes/paper_analysis", json={"profile_id": first["id"]}
        )
        self.assertEqual(bound.status_code, 200)

        service = LLMService()
        default_result = service.generate_text("paper_analysis", "hello")
        override_result = service.generate_text(
            "paper_analysis", "hello", profile_id=second["id"]
        )

        self.assertEqual(default_result.text, "gemini-test:hello")
        self.assertEqual(default_result.profile_id, first["id"])
        self.assertEqual(override_result.text, "openai-test:hello")

    def test_persisted_gemini_profile_falls_back_to_legacy_key(self):
        from app.core.llm.models import LLMProfile, LLMSceneBinding
        from app.core.llm.service import LLMService

        profile = LLMProfile(
            name="Legacy Gemini",
            protocol="gemini",
            model_name="gemini-legacy",
            enabled=True,
        )
        db.session.add(profile)
        db.session.flush()
        db.session.add(LLMSceneBinding(scene="paper_analysis", profile_id=profile.id))
        db.session.commit()

        with patch("app.core.llm.service.load_gemini_api_key", return_value="legacy-key"):
            result = LLMService().generate_text("paper_analysis", "hello")

        self.assertEqual(result.text, "gemini-legacy:hello")

    def test_rejects_invalid_protocol_and_missing_openai_base_url(self):
        invalid = self.client.post(
            "/api/llm/profiles",
            json={"name": "Bad", "protocol": "other", "model_name": "x"},
        )
        missing_url = self.client.post(
            "/api/llm/profiles",
            json={"name": "Bad OpenAI", "protocol": "openai", "model_name": "x"},
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(missing_url.status_code, 400)

    def test_profile_connection_test_uses_saved_secret(self):
        profile = self.client.post(
            "/api/llm/profiles",
            json={
                "name": "Testable",
                "protocol": "gemini",
                "model_name": "gemini-test",
                "api_key": "key",
            },
        ).get_json()["data"]

        response = self.client.post(f"/api/llm/profiles/{profile['id']}/test")

        self.assertEqual(response.status_code, 200)
        result = response.get_json()["data"]
        self.assertEqual(result["last_check_status"], "ok")
        self.assertNotIn('"api_key"', response.get_data(as_text=True))

    def test_cors_only_allows_local_frontend_origins(self):
        allowed = self.client.get(
            "/api/llm/profiles", headers={"Origin": "http://127.0.0.1:3000"}
        )
        blocked = self.client.get(
            "/api/llm/profiles", headers={"Origin": "https://malicious.example"}
        )

        self.assertEqual(
            allowed.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3000"
        )
        self.assertIsNone(blocked.headers.get("Access-Control-Allow-Origin"))


class LLMAdapterTestCase(unittest.TestCase):
    def test_env_secret_store_preserves_other_env_values(self):
        from app.core.llm.secrets import EnvSecretStore

        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OTHER_SETTING=keep\n", encoding="utf-8")
            store = EnvSecretStore(env_path)

            store.set(12, "secret-value")
            self.assertEqual(store.get(12), "secret-value")
            self.assertIn("OTHER_SETTING=keep", env_path.read_text(encoding="utf-8"))
            store.delete(12)
            self.assertIsNone(store.get(12))

    def test_openai_adapter_reads_chat_completion_content(self):
        from types import SimpleNamespace

        from app.core.llm.clients import OpenAICompatibleAdapter

        class Completions:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="openai-ok"))]
                )

        completions = Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        profile = SimpleNamespace(model_name="test-model", base_url="http://local/v1")

        result = OpenAICompatibleAdapter(profile, "secret", client=client).generate_text("hello")

        self.assertEqual(result, "openai-ok")
        self.assertEqual(completions.kwargs["model"], "test-model")

    def test_gemini_adapter_reads_generated_text(self):
        from types import SimpleNamespace

        from app.core.llm.clients import GeminiAdapter

        class Models:
            def generate_content(self, **kwargs):
                self.kwargs = kwargs
                return SimpleNamespace(text="gemini-ok")

        models = Models()
        profile = SimpleNamespace(model_name="gemini-test", base_url=None)

        result = GeminiAdapter(profile, "secret", client=SimpleNamespace(models=models)).generate_text(
            "hello"
        )

        self.assertEqual(result, "gemini-ok")
        self.assertEqual(models.kwargs["contents"], "hello")


if __name__ == "__main__":
    unittest.main()
