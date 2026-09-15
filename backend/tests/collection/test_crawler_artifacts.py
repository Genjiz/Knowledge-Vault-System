import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class CrawlerArtifactServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "artifacts"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.app.config["ARTIFACT_ROOT"] = str(self.temp_dir)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_exports_raw_issue_json_and_analysis_markdown(self):
        from app.collection.models import RawIssue, RawIssueAnalysis, RawPaper
        from app.collection.services.artifact_service import ArtifactService

        raw_issue = RawIssue(
            source_type="foreign",
            journal_name="Information Processing & Management",
            journal_slug="information-processing-and-management",
            year=2024,
            issue="6",
            volume="60",
            language="en",
            source_url="https://example.com/issue",
            paper_count=1,
        )
        db.session.add(raw_issue)
        db.session.flush()

        paper = RawPaper(
            raw_issue_id=raw_issue.id,
            title="Paper A",
            authors="Author One",
            abstract="Abstract A",
            detail_url="https://example.com/a",
            sort_index=0,
        )
        db.session.add(paper)

        analysis = RawIssueAnalysis(
            raw_issue=raw_issue,
            model_name="gemini-test",
            content_markdown="# Summary\n\nHello world",
            status="completed",
        )
        db.session.add(analysis)
        db.session.commit()

        artifact_service = ArtifactService()
        json_path = artifact_service.export_raw_issue(raw_issue)
        md_path = artifact_service.export_analysis(analysis)

        self.assertTrue(Path(json_path).exists())
        self.assertTrue(Path(md_path).exists())

        raw_payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
        markdown_payload = Path(md_path).read_text(encoding="utf-8")

        self.assertEqual(raw_payload["journal_name"], raw_issue.journal_name)
        self.assertEqual(raw_payload["papers"][0]["title"], "Paper A")
        self.assertEqual(markdown_payload, "# Summary\n\nHello world")

    def test_same_issue_number_in_different_volumes_uses_distinct_paths(self):
        from app.collection.models import RawIssue
        from app.collection.services.artifact_service import ArtifactService

        rows = [
            RawIssue(
                source_type="scopus",
                journal_name="IP&M",
                year=2026,
                volume=volume,
                issue="1",
                paper_count=0,
            )
            for volume in ("63", "64")
        ]
        db.session.add_all(rows)
        db.session.commit()

        paths = [ArtifactService().export_raw_issue(row) for row in rows]

        self.assertNotEqual(paths[0], paths[1])
        self.assertIn(str(Path("2026") / "63" / "1.json"), paths[0])
        self.assertIn(str(Path("2026") / "64" / "1.json"), paths[1])
        self.assertTrue(all(Path(path).is_file() for path in paths))


if __name__ == "__main__":
    unittest.main()
