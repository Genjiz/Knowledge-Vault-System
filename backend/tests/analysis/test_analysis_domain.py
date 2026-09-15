import hashlib
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


class FakeLLMService:
    def __init__(self):
        self.prompts = []

    def generate_text(self, scene, prompt, profile_id=None):
        from app.core.llm.service import GenerationResult

        self.prompts.append(prompt)
        return GenerationResult(text="# 分析结果", profile_id=profile_id or 1, model_name="fake")


class AnalysisDomainTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.temp_dir = Path(tempfile.gettempdir()) / "knowledge-vault-tests" / "analysis-domain"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True)
        self.app.config["PAPER_ANALYSIS_ARTIFACT_ROOT"] = str(self.temp_dir / "analyses")
        self.app.config["LITERATURE_TEXT_ASSET_ROOT"] = str(self.temp_dir / "text-assets")
        self.client = self.app.test_client()

        from app.core.llm.models import LLMProfile
        from app.papers.models import Journal, Literature

        profile = LLMProfile(
            name="分析域测试模型",
            protocol="gemini",
            model_name="gemini-analysis-domain-test",
            enabled=True,
        )
        db.session.add(profile)
        db.session.flush()
        self.profile_id = profile.id

        journal = Journal(name="IP&M", region="foreign")
        db.session.add(journal)
        db.session.flush()
        self.papers = [
            Literature(
                title="Volume 63 paper",
                authors="A",
                journal=journal.name,
                journal_id=journal.id,
                year=2026,
                volume="63",
                issue="1",
                abstract="Abstract A",
            ),
            Literature(
                title="Volume 64 paper",
                authors="B",
                journal=journal.name,
                journal_id=journal.id,
                year=2026,
                volume="64",
                issue="1",
                abstract="Abstract B",
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

    def test_issue_options_keep_same_issue_in_different_volumes_separate(self):
        rows = self.client.get("/api/paper-analyses/issues").get_json()["data"]

        self.assertEqual(
            [(row["volume"], row["issue"], row["paper_count"]) for row in rows],
            [("63", "1", 1), ("64", "1", 1)],
        )

    def test_default_prompt_template_is_visible_through_api(self):
        response = self.client.get("/api/paper-analyses/prompt-template")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertTrue(payload["version"])
        self.assertIn("核心研究主题", payload["content"])

    def test_custom_instruction_is_saved_and_composed_with_default_prompt(self):
        from app.analysis.services.analysis_service import PaperAnalysisService

        llm = FakeLLMService()
        service = PaperAnalysisService(llm_service=llm)
        analysis = service.create_analysis(
            literature_ids=[self.papers[0].id],
            issues=[],
            profile_id=self.profile_id,
            custom_instruction="重点比较研究方法，并输出表格。",
            include_fulltext=False,
        )

        completed = service.execute(analysis.id)

        self.assertEqual(completed.custom_instruction, "重点比较研究方法，并输出表格。")
        self.assertIn("核心研究主题", completed.prompt_template_snapshot)
        self.assertFalse(completed.include_fulltext)
        self.assertIn("核心研究主题", llm.prompts[0])
        self.assertIn("重点比较研究方法，并输出表格。", llm.prompts[0])

    def test_fulltext_extraction_falls_back_and_reuses_versioned_asset(self):
        from app.analysis.services.text_extraction_service import (
            ExtractionResult,
            LiteratureTextExtractionService,
        )

        pdf = self.temp_dir / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 fixture")
        paper = self.papers[0]
        paper.pdf_path = str(pdf)
        paper.pdf_sha256 = hashlib.sha256(pdf.read_bytes()).hexdigest()
        db.session.commit()
        calls = []

        class FailedExtractor:
            name = "pymupdf4llm"
            version = "test-1"

            def extract(self, path):
                calls.append((self.name, path))
                raise ValueError("two-column order failed")

        class WorkingExtractor:
            name = "docling"
            version = "test-2"

            def extract(self, path):
                calls.append((self.name, path))
                return ExtractionResult(markdown="# Paper\n\nFull text", page_count=3)

        service = LiteratureTextExtractionService(
            extractors=[FailedExtractor(), WorkingExtractor()],
            pipeline_version="academic-markdown-v1",
        )
        first = service.get_or_extract(paper)
        second = service.get_or_extract(paper)

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.extractor_name, "docling")
        self.assertEqual(first.extractor_version, "test-2")
        self.assertEqual(first.status, "completed")
        self.assertEqual(first.page_count, 3)
        self.assertEqual(len(calls), 2)
        self.assertEqual(Path(first.markdown_path).read_text(encoding="utf-8"), "# Paper\n\nFull text")
        self.assertIn("pymupdf4llm", first.attempts_json)

    def test_same_pdf_hash_is_reused_across_literatures(self):
        from app.analysis.services.text_extraction_service import (
            ExtractionResult,
            LiteratureTextExtractionService,
        )

        pdf = self.temp_dir / "shared.pdf"
        pdf.write_bytes(b"%PDF-1.4 shared fixture")
        for paper in self.papers:
            paper.pdf_path = str(pdf)
        db.session.commit()
        calls = []

        class WorkingExtractor:
            name = "fake"
            version = "1"

            def extract(self, path):
                calls.append(path)
                return ExtractionResult(markdown="# Shared paper")

        service = LiteratureTextExtractionService(
            extractors=[WorkingExtractor()],
            pipeline_version="shared-v1",
        )

        first = service.get_or_extract(self.papers[0])
        second = service.get_or_extract(self.papers[1])

        self.assertEqual(first.id, second.id)
        self.assertEqual(len(calls), 1)

    def test_analysis_with_fulltext_sends_cached_markdown_to_model(self):
        from app.analysis.models import LiteratureTextAsset
        from app.analysis.services.analysis_service import PaperAnalysisService

        markdown_path = self.temp_dir / "cached.md"
        markdown_path.write_text("# Full paper\n\nEvidence from the PDF.", encoding="utf-8")
        paper = self.papers[0]
        paper.pdf_path = str(self.temp_dir / "paper.pdf")
        db.session.commit()

        class FakeTextService:
            def get_or_extract(self, literature):
                asset = LiteratureTextAsset(
                    literature_id=literature.id,
                    source_pdf_sha256="a" * 64,
                    pipeline_version="test-v1",
                    extractor_name="fake",
                    extractor_version="1",
                    markdown_path=str(markdown_path),
                    markdown_sha256="b" * 64,
                    status="completed",
                    char_count=37,
                )
                db.session.add(asset)
                db.session.commit()
                return asset

            @staticmethod
            def read_markdown(asset):
                return Path(asset.markdown_path).read_text(encoding="utf-8")

        llm = FakeLLMService()
        service = PaperAnalysisService(
            llm_service=llm,
            text_extraction_service=FakeTextService(),
        )
        analysis = service.create_analysis(
            literature_ids=[paper.id],
            issues=[],
            profile_id=self.profile_id,
            include_fulltext=True,
        )

        completed = service.execute(analysis.id)

        self.assertEqual(completed.fulltext_count, 1)
        self.assertIsNotNone(completed.items[0].text_asset_id)
        self.assertIn("Evidence from the PDF.", llm.prompts[0])

    def test_oversized_fulltext_is_split_before_model_calls(self):
        from app.analysis.models import LiteratureTextAsset
        from app.analysis.services.analysis_service import PaperAnalysisService

        markdown_path = self.temp_dir / "large-cached.md"
        markdown_path.write_text("~" * 900, encoding="utf-8")
        paper = self.papers[0]
        paper.pdf_path = str(self.temp_dir / "large-paper.pdf")
        db.session.commit()

        class FakeTextService:
            def get_or_extract(self, literature):
                asset = LiteratureTextAsset(
                    literature_id=literature.id,
                    source_pdf_sha256="c" * 64,
                    pipeline_version="test-v1",
                    extractor_name="fake",
                    extractor_version="1",
                    markdown_path=str(markdown_path),
                    markdown_sha256="d" * 64,
                    status="completed",
                    char_count=900,
                )
                db.session.add(asset)
                db.session.commit()
                return asset

            @staticmethod
            def read_markdown(asset):
                return Path(asset.markdown_path).read_text(encoding="utf-8")

        llm = FakeLLMService()
        service = PaperAnalysisService(
            llm_service=llm,
            text_extraction_service=FakeTextService(),
            max_batch_chars=300,
        )
        analysis = service.create_analysis(
            literature_ids=[paper.id],
            issues=[],
            profile_id=self.profile_id,
            include_fulltext=True,
        )

        service.execute(analysis.id)

        # 多个初步分析调用之后还有一次综合调用。
        self.assertGreater(len(llm.prompts), 2)
        initial_prompts = llm.prompts[:-1]
        self.assertTrue(all(len(prompt) < 1000 for prompt in initial_prompts))
        self.assertEqual(sum(prompt.count("~") for prompt in initial_prompts), 900)

    def test_fulltext_extraction_failure_is_visible_on_completed_analysis(self):
        from app.analysis.services.analysis_service import PaperAnalysisService
        from app.analysis.services.text_extraction_service import TextExtractionError

        paper = self.papers[0]
        paper.pdf_path = str(self.temp_dir / "broken.pdf")
        db.session.commit()

        class FailedTextService:
            def get_or_extract(self, literature):
                raise TextExtractionError("两种解析器均失败")

        service = PaperAnalysisService(
            llm_service=FakeLLMService(),
            text_extraction_service=FailedTextService(),
        )
        analysis = service.create_analysis(
            literature_ids=[paper.id],
            issues=[],
            profile_id=self.profile_id,
            include_fulltext=True,
        )

        completed = service.execute(analysis.id)

        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.fulltext_count, 0)
        self.assertEqual(completed.fulltext_failed_count, 1)
        self.assertIn("Volume 63 paper", completed.fulltext_error_message)
        payload = completed.to_dict()
        self.assertEqual(payload["fulltext_failed_count"], 1)
        self.assertIn("两种解析器均失败", payload["fulltext_error_message"])


if __name__ == "__main__":
    unittest.main()
