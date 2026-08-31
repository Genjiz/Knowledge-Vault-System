import sys
import tempfile
import tempfile
import textwrap
import unittest
from pathlib import Path
import shutil

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class ProviderModuleLoadingTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "provider-module-loading"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_foreign_provider_import_module_supports_sibling_imports(self):
        from app.collection.sources.elsevier import ElsevierSource

        temp_path = self.temp_root / "foreign"
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "sibling_dep.py").write_text("VALUE = 42\n", encoding="utf-8")
        (temp_path / "loader_target.py").write_text(
            textwrap.dedent(
                """
                import sibling_dep

                ANSWER = sibling_dep.VALUE
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        provider = ElsevierSource()
        module = provider._import_module("loader_target", [str(temp_path), "loader_target.py"])

        self.assertEqual(module.ANSWER, 42)

    def test_domestic_provider_default_loader_supports_sibling_imports(self):
        from app.collection.sources.ncpssd import NcpssdSource

        temp_path = self.temp_root / "domestic"
        temp_path.mkdir(parents=True, exist_ok=True)
        (temp_path / "dep.py").write_text("class BaseCrawler:\n    pass\n", encoding="utf-8")
        target_script = temp_path / "domestic_loader.py"
        target_script.write_text(
            textwrap.dedent(
                """
                from dep import BaseCrawler

                class JournalPaperInfoCrawler(BaseCrawler):
                    pass
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        provider = NcpssdSource()
        provider._crawler_factory = None
        provider._default_script_path = target_script

        factory = provider._load_default_factory()

        self.assertEqual(factory.__name__, "JournalPaperInfoCrawler")


if __name__ == "__main__":
    unittest.main()
