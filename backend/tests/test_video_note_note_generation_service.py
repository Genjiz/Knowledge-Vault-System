import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.collection.sources.base import ProviderError
from app.video_notes.services.note_generation_service import NoteGenerationService


class _TimeoutStream:
    def __iter__(self):
        return self

    def __next__(self):
        raise OSError("[WinError 10060] connection timed out")


class _FakeModels:
    def generate_content_stream(self, **kwargs):
        return _TimeoutStream()


class _FakeClient:
    def __init__(self):
        self.models = _FakeModels()


class NoteGenerationServiceTestCase(unittest.TestCase):
    def test_normalize_markdown_strips_preface_and_fences(self):
        service = NoteGenerationService(client=_FakeClient(), model_name="gemini-2.5-flash")

        raw = "好的，这是一份整理结果：\n\n```markdown\n# 标题\n\n- 要点\n```\n"
        self.assertEqual(service._normalize_markdown(raw), "# 标题\n\n- 要点")

    def test_normalize_markdown_keeps_content_from_first_heading(self):
        service = NoteGenerationService(client=_FakeClient(), model_name="gemini-2.5-flash")

        raw = "根据字幕生成如下笔记：\n\n---\n\n# 标题\n\n## 小节\n"
        self.assertEqual(service._normalize_markdown(raw), "# 标题\n\n## 小节")

    def test_generate_note_surfaces_proxy_guidance_on_timeout(self):
        service = NoteGenerationService(client=_FakeClient(), model_name="gemini-2.5-flash")

        with self.assertRaises(ProviderError) as ctx:
            service.generate_note(
                transcript_text="hello",
                source_url="https://www.bilibili.com/video/BV1qdXoBdEYy/",
                bvid="BV1qdXoBdEYy",
                video_title="test",
            )

        message = str(ctx.exception)
        self.assertIn("generativelanguage.googleapis.com:443", message)
        self.assertIn("HTTPS_PROXY/HTTP_PROXY", message)


if __name__ == "__main__":
    unittest.main()
