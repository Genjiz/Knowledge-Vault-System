import sys
import shutil
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class RecordingExecutor:
    def __init__(self):
        self.calls = []

    def submit(self, task_id, fn, on_error=None):
        self.calls.append((task_id, fn, on_error))
        return None


class FakeLLMService:
    def __init__(self):
        self.prompts = []

    def generate_text(self, scene, prompt, profile_id=None):
        from app.core.llm.service import GenerationResult

        self.prompts.append((scene, prompt, profile_id))
        return GenerationResult(
            text=f"# Result {len(self.prompts)}",
            profile_id=profile_id or 7,
            model_name="fake-model",
        )


class PaperAnalysisTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.executor = RecordingExecutor()
        self.app.config["PAPER_ANALYSIS_EXECUTOR"] = self.executor
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "paper-analysis"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.app.config["PAPER_ANALYSIS_ARTIFACT_ROOT"] = str(self.temp_dir)
        self.client = self.app.test_client()

        from app.papers.models import Journal, Literature

        journal = Journal(name="情报学报", region="domestic")
        db.session.add(journal)
        db.session.flush()
        self.journal_id = journal.id
        self.papers = [
            Literature(
                title="论文一",
                authors="作者甲",
                journal="情报学报",
                journal_id=journal.id,
                year=2026,
                issue="1",
                abstract="摘要一",
                keywords="关键词一",
            ),
            Literature(
                title="论文二",
                authors="作者乙",
                journal="情报学报",
                journal_id=journal.id,
                year=2026,
                issue="1",
                abstract="摘要二",
                keywords="关键词二",
            ),
            Literature(
                title="论文三",
                authors="作者丙",
                journal="情报学报",
                journal_id=journal.id,
                year=2026,
                issue="2",
                abstract=None,
            ),
        ]
        db.session.add_all(self.papers)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_issue_options_group_unified_literatures(self):
        response = self.client.get("/api/paper-analyses/issues")

        self.assertEqual(response.status_code, 200)
        rows = response.get_json()["data"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["paper_count"], 2)

    def test_issue_options_exclude_blank_journal_or_issue(self):
        from app.papers.models import Literature

        db.session.add(Literature(title="不完整题录", authors="作者", journal="", year=2026, issue=""))
        db.session.commit()

        rows = self.client.get("/api/paper-analyses/issues").get_json()["data"]

        self.assertEqual(len(rows), 2)

    def test_issue_selection_includes_manual_paper_without_journal_id(self):
        from app.papers.models import Literature

        manual = Literature(
            title="手工论文",
            authors="作者丁",
            journal="情报学报",
            journal_id=None,
            year=2026,
            issue="1",
            abstract="手工摘要",
        )
        db.session.add(manual)
        db.session.commit()

        rows = self.client.get("/api/paper-analyses/issues").get_json()["data"]
        first_issue = next(row for row in rows if row["issue"] == "1")
        preview = self.client.post(
            "/api/paper-analyses/selection-preview", json={"issues": [first_issue]}
        ).get_json()["data"]

        self.assertEqual(first_issue["paper_count"], 3)
        self.assertEqual({paper["id"] for paper in preview}, {self.papers[0].id, self.papers[1].id, manual.id})

    def test_create_expands_issues_and_deduplicates_explicit_papers(self):
        response = self.client.post(
            "/api/paper-analyses",
            json={
                "title": "跨期分析",
                "literature_ids": [self.papers[0].id, self.papers[2].id],
                "issues": [
                    {
                        "journal_id": self.journal_id,
                        "year": 2026,
                        "issue": "1",
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        analysis = response.get_json()["data"]
        self.assertEqual(analysis["paper_count"], 3)
        self.assertEqual(analysis["status"], "queued")
        self.assertEqual(len(analysis["items"]), 3)
        self.assertEqual(len(self.executor.calls), 1)

    def test_create_rejects_empty_selection(self):
        response = self.client.post("/api/paper-analyses", json={})
        self.assertEqual(response.status_code, 400)

    def test_create_rejects_unknown_profile(self):
        response = self.client.post(
            "/api/paper-analyses",
            json={"literature_ids": [self.papers[0].id], "profile_id": 999},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("模型档案不存在", response.get_json()["message"])

    def test_execute_batches_large_input_and_saves_result(self):
        from app.papers.services.analysis_service import PaperAnalysisService

        llm = FakeLLMService()
        service = PaperAnalysisService(llm_service=llm, max_batch_chars=30)
        analysis = service.create_analysis(
            literature_ids=[paper.id for paper in self.papers],
            issues=[],
            title="Batch test",
        )

        completed = service.execute(analysis.id)

        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.model_name, "fake-model")
        self.assertGreater(len(llm.prompts), 1)
        self.assertIn("# Result", completed.content_markdown)
        self.assertTrue(completed.artifact_md_path)
        self.assertTrue(Path(completed.artifact_md_path).exists())

    def test_list_and_get_return_history_with_snapshots(self):
        from app.papers.services.analysis_service import PaperAnalysisService

        service = PaperAnalysisService(llm_service=FakeLLMService())
        analysis = service.create_analysis(
            literature_ids=[self.papers[0].id], issues=[], title="Saved"
        )

        listed = self.client.get("/api/paper-analyses").get_json()["data"]
        detail = self.client.get(f"/api/paper-analyses/{analysis.id}").get_json()["data"]

        self.assertEqual(listed["total"], 1)
        self.assertEqual(detail["title"], "Saved")
        self.assertEqual(detail["items"][0]["title"], "论文一")


if __name__ == "__main__":
    unittest.main()
