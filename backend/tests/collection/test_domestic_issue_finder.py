import importlib.util
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load_issue_finder_class():
    module_path = (
        BACKEND_DIR
        / "app"
        / "collection"
        / "legacy"
        / "domestic"
        / "2.issue_url_finder.py"
    )
    spec = importlib.util.spec_from_file_location("legacy_issue_url_finder", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.IssueUrlFinder


class IssueUrlFinderTestCase(unittest.TestCase):
    def setUp(self):
        IssueUrlFinder = _load_issue_finder_class()
        self.finder = IssueUrlFinder(min_delay=0, max_delay=0)

    def test_extract_search_candidates_prefers_exact_issue(self):
        html = """
        <div class="journal-item">
            <a href="/journal/secure/details?params=wrong">Journal A</a>
            <span>2024 / 5</span>
        </div>
        <div class="journal-item">
            <a href="/journal/secure/details?params=right">Journal A</a>
            <span>2024 / 6</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        candidates = self.finder._extract_issue_candidates_from_search_page(
            soup=soup,
            target_journal_name="Journal A",
            target_year=2024,
            target_issue=6,
        )
        self.assertEqual(len(candidates), 2)

        top = max(candidates, key=lambda item: item["score"])
        self.assertEqual(top["params"], "right")
        self.assertTrue(top["journal_match"])
        self.assertTrue(top["year_match"])
        self.assertTrue(top["issue_match"])

    def test_cache_key_is_strict_journal_name_match(self):
        key_a = self.finder._get_cache_key("Journal A", 2024, 6)
        key_b = self.finder._get_cache_key("Journal A ", 2024, 6)
        key_c = self.finder._get_cache_key("Journal-B", 2024, 6)
        self.assertEqual(key_a, key_b)
        self.assertNotEqual(key_a, key_c)

    def test_match_issue_token_supports_common_formats(self):
        self.assertTrue(self.finder._match_issue_token("2024年第6期", 6))
        self.assertTrue(self.finder._match_issue_token("2024 / 6", 6))
        self.assertTrue(self.finder._match_issue_token(" 06 ", 6))
        self.assertFalse(self.finder._match_issue_token("2024年第8期", 6))


if __name__ == "__main__":
    unittest.main()
