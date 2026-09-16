import json
import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


class EnvironmentBootstrapContractTests(unittest.TestCase):
    def test_generated_dependency_directories_are_ignored(self):
        ignore_lines = {
            line.strip()
            for line in (ROOT_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertIn(".venv/", ignore_lines)
        self.assertIn("frontend/node_modules/", ignore_lines)

    def test_python_dependency_tree_is_exactly_pinned(self):
        requirements = (ROOT_DIR / "backend" / "requirements.txt").read_text(
            encoding="utf-8"
        )
        dependency_lines = [
            line.strip()
            for line in requirements.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertGreater(len(dependency_lines), 18)
        for dependency in dependency_lines:
            self.assertRegex(
                dependency,
                r"^[A-Za-z0-9_.-]+==[^\s]+$",
                f"依赖未精确锁定：{dependency}",
            )

    def test_runtime_versions_are_declared(self):
        self.assertRegex(
            (ROOT_DIR / ".python-version").read_text(encoding="utf-8").strip(),
            r"^3\.13\.\d+$",
        )
        self.assertRegex(
            (ROOT_DIR / ".node-version").read_text(encoding="utf-8").strip(),
            r"^24\.\d+\.\d+$",
        )

        package = json.loads(
            (ROOT_DIR / "frontend" / "package.json").read_text(encoding="utf-8")
        )
        self.assertEqual(package["engines"]["node"], "24.17.0")
        self.assertEqual(package["engines"]["npm"], "11.13.0")

    def test_setup_script_covers_the_rebuild_workflow(self):
        script = (ROOT_DIR / "setup.ps1").read_text(encoding="utf-8")

        # Windows PowerShell 5.1 会按系统代码页读取无 BOM 文件，脚本须保持 ASCII。
        script.encode("ascii")

        for expected_fragment in (
            "python -m venv",
            "backend\\requirements.txt",
            "npm ci",
            ".env.example",
            "db upgrade head",
            "npm run build",
        ):
            self.assertIn(expected_fragment, script)


if __name__ == "__main__":
    unittest.main()
