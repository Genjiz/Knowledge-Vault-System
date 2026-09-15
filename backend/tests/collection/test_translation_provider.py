import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TranslationProviderTestCase(unittest.TestCase):
    def test_translate_papers_returns_index_aligned_translations(self):
        from app.collection.providers.translation_provider import TranslationProvider

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

    def test_translate_papers_passes_explicit_profile_to_llm_service(self):
        from app.collection.providers.translation_provider import TranslationProvider
        from app.core.llm.service import GenerationResult

        class FakeLLMService:
            def __init__(self):
                self.calls = []

            def generate_text(self, scene, prompt, profile_id=None):
                self.calls.append((scene, profile_id))
                return GenerationResult(
                    text='{"papers":[]}',
                    profile_id=profile_id,
                    model_name="selected-model",
                )

        llm = FakeLLMService()
        provider = TranslationProvider(llm_service=llm)

        provider.translate_papers([], profile_id=42)

        self.assertEqual(llm.calls, [("paper_translation", 42)])
        self.assertEqual(provider.model_name, "selected-model")


if __name__ == "__main__":
    unittest.main()
