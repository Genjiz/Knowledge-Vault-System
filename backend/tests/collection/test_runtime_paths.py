import os
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path
import shutil
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class RuntimePathTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "runtime-paths"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.original_browser_data_root = os.environ.get("CRAWLER_BROWSER_DATA_ROOT")
        self.original_browser_path = os.environ.get("CRAWLER_BROWSER_PATH")

    def tearDown(self):
        if self.original_browser_data_root is None:
            os.environ.pop("CRAWLER_BROWSER_DATA_ROOT", None)
        else:
            os.environ["CRAWLER_BROWSER_DATA_ROOT"] = self.original_browser_data_root

        if self.original_browser_path is None:
            os.environ.pop("CRAWLER_BROWSER_PATH", None)
        else:
            os.environ["CRAWLER_BROWSER_PATH"] = self.original_browser_path

        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_workspace_root_points_to_flattened_project_root(self):
        from app.collection.runtime.paths import get_workspace_root

        root = get_workspace_root()

        self.assertTrue((root / "backend").exists())
        self.assertTrue((root / "frontend").exists())

    def test_project_root_matches_workspace_root_after_flattening(self):
        from app.collection.runtime.paths import get_project_root, get_workspace_root

        self.assertEqual(get_project_root(), get_workspace_root())

    def test_browser_data_root_supports_environment_override(self):
        from app.collection.runtime.paths import get_browser_data_root

        override = self.temp_root / "browser-data"
        os.environ["CRAWLER_BROWSER_DATA_ROOT"] = str(override)

        self.assertEqual(get_browser_data_root(), override)

    def test_browser_data_root_defaults_to_project_profile_directory(self):
        import app.collection.runtime.paths as runtime_paths

        workspace_root = self.temp_root / "workspace"
        project_default = workspace_root / ".crawler-browser-profile"
        os.environ.pop("CRAWLER_BROWSER_DATA_ROOT", None)

        with patch.object(runtime_paths, "get_workspace_root", return_value=workspace_root):
            self.assertEqual(runtime_paths.get_browser_data_root(), project_default)

    def test_find_chrome_executable_supports_environment_override(self):
        from app.collection.runtime.paths import find_chrome_executable

        fake_chrome = self.temp_root / "chrome.exe"
        fake_chrome.write_text("", encoding="utf-8")
        os.environ["CRAWLER_BROWSER_PATH"] = str(fake_chrome)

        self.assertEqual(find_chrome_executable(), fake_chrome)


if __name__ == "__main__":
    unittest.main()
