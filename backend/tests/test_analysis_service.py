import shutil
import sys
import tempfile
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class AnalysisServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "analysis-artifacts"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.app.config["ARTIFACT_ROOT"] = str(self.temp_dir)
        self.ctx = self.app.app_context()
        self.ctx.push()
        from app.collection.models import RawIssue, RawPaper  # noqa: F401

        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_analyze_issue_saves_analysis_and_exports_markdown(self):
        from app.collection.models import RawIssue, RawPaper
        from app.collection.services.analysis_service import AnalysisService

        raw_issue = RawIssue(
            source_type="foreign",
            journal_name="Information Processing & Management",
            year=2024,
            issue="6",
            language="en",
            paper_count=2,
        )
        db.session.add(raw_issue)
        db.session.flush()

        db.session.add_all(
            [
                RawPaper(
                    raw_issue_id=raw_issue.id,
                    title="Paper A",
                    abstract="Abstract A",
                    authors="Author One",
                    keywords_json='["k1"]',
                    sort_index=0,
                ),
                RawPaper(
                    raw_issue_id=raw_issue.id,
                    title="Paper B",
                    abstract="Abstract B",
                    authors="Author Two",
                    keywords_json='["k2"]',
                    sort_index=1,
                ),
            ]
        )
        db.session.commit()

        class FakeAnalysisProvider:
            model_name = "fake-gemini"

            def generate_analysis(self, raw_issue, papers):
                self.last_issue = raw_issue
                self.last_papers = papers
                return "# Analysis\n\nGenerated summary"

        service = AnalysisService(provider=FakeAnalysisProvider())
        analysis = service.analyze_issue(raw_issue.id)

        self.assertEqual(analysis.status, "completed")
        self.assertEqual(analysis.model_name, "fake-gemini")
        self.assertEqual(analysis.content_markdown, "# Analysis\n\nGenerated summary")
        self.assertTrue(analysis.artifact_md_path)
        self.assertTrue(Path(analysis.artifact_md_path).exists())
        self.assertEqual(raw_issue.analysis_status, "completed")


if __name__ == "__main__":
    unittest.main()
