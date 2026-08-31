import os
import shutil
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class GeminiRuntimeTestCase(unittest.TestCase):
    def setUp(self):
        self.env_names = (
            "GEMINI_API_KEY",
            "GEMINI_PROXY_URL",
            "HTTPS_PROXY",
            "HTTP_PROXY",
            "https_proxy",
            "http_proxy",
        )
        self.saved_env = {name: os.environ.get(name) for name in self.env_names}
        for name in self.env_names:
            os.environ.pop(name, None)
        self.temp_root = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "gemini-runtime"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        from app.core.llm import gemini

        gemini.load_runtime_env.cache_clear()
        for name in self.env_names:
            os.environ.pop(name, None)
            if self.saved_env[name] is not None:
                os.environ[name] = self.saved_env[name]
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_load_gemini_api_key_from_root_dotenv(self):
        from app.core.llm import gemini

        root = self.temp_root / "api-key"
        root.mkdir(parents=True, exist_ok=True)
        (root / ".env").write_text("GEMINI_API_KEY=dotenv-test-key\n", encoding="utf-8")

        with patch.object(gemini, "get_project_root", return_value=root), patch.object(
            gemini, "get_workspace_root", return_value=root
        ):
            gemini.load_runtime_env.cache_clear()
            self.assertEqual(gemini.load_gemini_api_key(), "dotenv-test-key")

    def test_create_gemini_client_uses_proxy_from_dotenv(self):
        from app.core.llm import gemini

        class FakeHttpOptions:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeTypesModule:
            HttpOptions = FakeHttpOptions

        class FakeGenaiModule:
            captured_kwargs = None

            @staticmethod
            def Client(**kwargs):
                FakeGenaiModule.captured_kwargs = kwargs
                return kwargs

        def fake_import_module(name):
            if name == "google.genai":
                return FakeGenaiModule
            if name == "google.genai.types":
                return FakeTypesModule
            raise AssertionError(f"Unexpected import: {name}")

        root = self.temp_root / "proxy"
        root.mkdir(parents=True, exist_ok=True)
        (root / ".env").write_text(
            "GEMINI_API_KEY=dotenv-test-key\nGEMINI_PROXY_URL=http://127.0.0.1:7890\n",
            encoding="utf-8",
        )

        with patch.object(gemini, "get_project_root", return_value=root), patch.object(
            gemini, "get_workspace_root", return_value=root
        ), patch.object(gemini.importlib, "import_module", side_effect=fake_import_module):
            gemini.load_runtime_env.cache_clear()
            result = gemini.create_gemini_client()

        self.assertEqual(result["api_key"], "dotenv-test-key")
        http_options = result["http_options"]
        self.assertEqual(http_options.kwargs["clientArgs"]["proxy"], "http://127.0.0.1:7890")
        self.assertEqual(http_options.kwargs["asyncClientArgs"]["proxy"], "http://127.0.0.1:7890")
        self.assertFalse(http_options.kwargs["clientArgs"]["trust_env"])
        self.assertFalse(http_options.kwargs["asyncClientArgs"]["trust_env"])


if __name__ == "__main__":
    unittest.main()
