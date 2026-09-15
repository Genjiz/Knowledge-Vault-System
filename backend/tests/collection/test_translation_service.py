import json
import shutil
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class TranslationServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "translation-artifacts"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.app.config["ARTIFACT_ROOT"] = str(self.temp_dir)
        self.ctx = self.app.app_context()
        self.ctx.push()
        from app.collection.models import RawIssue, RawPaper  # noqa: F401
        from app.core.llm.models import LLMProfile

        db.create_all()
        profile = LLMProfile(
            name="翻译测试模型",
            protocol="gemini",
            model_name="selected-model",
            enabled=True,
        )
        db.session.add(profile)
        db.session.commit()
        self.profile_id = profile.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_translate_issue_updates_fields_and_regenerates_json(self):
        from app.collection.models import RawIssue, RawPaper
        from app.collection.services.artifact_service import ArtifactService
        from app.collection.services.translation_service import TranslationService

        raw_issue = RawIssue(
            source_type="foreign",
            journal_name="Information Processing & Management",
            year=2024,
            issue="6",
            language="en",
            paper_count=1,
        )
        db.session.add(raw_issue)
        db.session.flush()

        paper = RawPaper(
            raw_issue_id=raw_issue.id,
            title="Paper A",
            abstract="Abstract A",
            authors="Author One",
            sort_index=0,
        )
        db.session.add(paper)
        db.session.commit()

        ArtifactService().export_raw_issue(raw_issue)

        class FakeTranslationProvider:
            model_name = None

            def translate_papers(self, papers, profile_id):
                self.model_name = "selected-model"
                return [
                    {
                        "title_zh": "论文A",
                        "abstract_zh": "摘要A",
                    }
                ]

        service = TranslationService(provider=FakeTranslationProvider())
        updated_issue = service.translate_issue(raw_issue.id, profile_id=self.profile_id)

        self.assertEqual(updated_issue.translation_status, "completed")
        self.assertEqual(updated_issue.papers[0].title_zh, "论文A")
        self.assertEqual(updated_issue.papers[0].translation_status, "completed")
        self.assertEqual(updated_issue.translation_profile_id, self.profile_id)
        self.assertEqual(updated_issue.translation_model_name, "selected-model")

        payload = json.loads(Path(updated_issue.raw_json_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["papers"][0]["title_zh"], "论文A")


if __name__ == "__main__":
    unittest.main()
