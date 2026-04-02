import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TranslationProviderTestCase(unittest.TestCase):
    def test_translate_papers_returns_index_aligned_translations(self):
        from app.crawler.providers.translation_provider import TranslationProvider

        class FakeChunk:
            def __init__(self, text):
                self.candidates = [type("Candidate", (), {"content": type("Content", (), {"parts": [type("Part", (), {"text": text})()]})()})()]

        class FakeClient:
            class models:
                @staticmethod
                def generate_content_stream(model, contents, config):
                    return [FakeChunk('{"papers":[{"index":0,"title_zh":"论文A","abstract_zh":"摘要A"}]}')]

        provider = TranslationProvider(client=FakeClient(), model_name="fake-gemini")
        result = provider.translate_papers(
            [
                {
                    "title": "Paper A",
                    "abstract": "Abstract A",
                }
            ]
        )

        self.assertEqual(result[0]["title_zh"], "论文A")
        self.assertEqual(result[0]["abstract_zh"], "摘要A")


if __name__ == "__main__":
    unittest.main()
