import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class BalancedInlineMarkupTestCase(unittest.TestCase):
    def test_strips_balanced_allowed_tags_and_decodes_entities(self):
        from app.core.text import clean_title_text

        self.assertEqual(
            clean_title_text("基于<bold>XGBoost</bold>与<italic>A&amp;B</italic>的方法"),
            "基于XGBoost与A&B的方法",
        )

    def test_supports_correctly_nested_tags(self):
        from app.core.text import clean_title_text

        self.assertEqual(clean_title_text("<bold>A<sup>2</sup></bold>模型"), "A2模型")

    def test_preserves_unbalanced_or_misnested_markup(self):
        from app.core.text import clean_title_text

        values = [
            "基于<bold>XGBoost的方法",
            "基于XGBoost</bold>的方法",
            "<bold><italic>模型</bold></italic>",
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(clean_title_text(value), value)

    def test_preserves_unknown_tags(self):
        from app.core.text import clean_title_text

        self.assertEqual(clean_title_text("基于<em>模型</em>的方法"), "基于<em>模型</em>的方法")


if __name__ == "__main__":
    unittest.main()
