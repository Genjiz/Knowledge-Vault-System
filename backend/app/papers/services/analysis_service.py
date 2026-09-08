from datetime import UTC, datetime
from pathlib import Path

from flask import current_app

from app.core.extensions import db
from app.core.llm.service import LLMService
from app.core.llm.models import LLMProfile
from app.core.paths import artifacts_root
from app.papers.models import Literature
from app.papers.models.paper_analysis import PaperAnalysis, PaperAnalysisItem


class PaperAnalysisService:
    def __init__(self, llm_service=None, max_batch_chars=40000):
        self.llm_service = llm_service or LLMService()
        self.max_batch_chars = max_batch_chars

    def select_literatures(self, literature_ids=None, issues=None):
        selected = []
        seen = set()

        ids = [int(value) for value in (literature_ids or []) if str(value).isdigit()]
        if ids:
            by_id = {row.id: row for row in Literature.query.filter(Literature.id.in_(ids)).all()}
            for literature_id in ids:
                if literature_id in by_id and literature_id not in seen:
                    selected.append(by_id[literature_id])
                    seen.add(literature_id)

        for issue in issues or []:
            year = issue.get("year")
            number = str(issue.get("issue") or "").strip()
            if not year or not number:
                continue
            query = Literature.query.filter(Literature.year == int(year), Literature.issue == number)
            journal = str(issue.get("journal") or "").strip()
            journal_id = issue.get("journal_id")
            if journal:
                query = query.filter(Literature.journal == journal)
            elif journal_id:
                query = query.filter(Literature.journal_id == int(journal_id))
            else:
                continue
            for literature in query.order_by(Literature.id).all():
                if literature.id not in seen:
                    selected.append(literature)
                    seen.add(literature.id)
        return selected

    def create_analysis(self, *, literature_ids, issues, title=None, profile_id=None):
        if profile_id is not None:
            profile = db.session.get(LLMProfile, int(profile_id))
            if profile is None:
                raise ValueError("模型档案不存在")
            if not profile.enabled:
                raise ValueError("所选模型档案已停用")
        papers = self.select_literatures(literature_ids, issues)
        if not papers:
            raise ValueError("请至少选择一篇论文")
        analysis = PaperAnalysis(
            title=(title or "").strip() or self._default_title(papers),
            status="queued",
            profile_id=profile_id,
            paper_count=len(papers),
        )
        db.session.add(analysis)
        db.session.flush()
        db.session.add_all(
            [PaperAnalysisItem.from_literature(analysis.id, paper, index) for index, paper in enumerate(papers)]
        )
        db.session.commit()
        db.session.refresh(analysis)
        return analysis

    def clone_analysis(self, analysis_id, profile_id=None):
        source = db.session.get(PaperAnalysis, analysis_id)
        if source is None:
            raise ValueError("分析任务不存在")
        analysis = PaperAnalysis(
            title=f"{source.title}（重新分析）",
            status="queued",
            profile_id=profile_id if profile_id is not None else source.profile_id,
            paper_count=len(source.items),
        )
        db.session.add(analysis)
        db.session.flush()
        db.session.add_all([item.clone_for(analysis.id) for item in source.items])
        db.session.commit()
        db.session.refresh(analysis)
        return analysis

    @staticmethod
    def _default_title(papers):
        issues = {(paper.journal, paper.year, paper.issue) for paper in papers}
        if len(issues) == 1:
            journal, year, issue = next(iter(issues))
            if journal and year and issue:
                return f"{journal} {year} 年第 {issue} 期分析"
        return f"{len(papers)} 篇论文综合分析"

    @staticmethod
    def _format_item(item, index):
        return "\n".join(
            [
                f"Paper {index}",
                f"Title: {item.title or 'N/A'}",
                f"Authors: {item.authors or 'N/A'}",
                f"Journal: {item.journal or 'N/A'}",
                f"Year/Issue: {item.year or 'N/A'} / {item.issue or 'N/A'}",
                f"Abstract: {item.abstract or 'N/A'}",
                f"Keywords: {item.keywords or 'N/A'}",
            ]
        )

    def _batches(self, items):
        batches, current, current_size = [], [], 0
        for index, item in enumerate(items, 1):
            text = self._format_item(item, index)
            if current and current_size + len(text) > self.max_batch_chars:
                batches.append(current)
                current, current_size = [], 0
            current.append((index, text))
            current_size += len(text)
        if current:
            batches.append(current)
        return batches

    @staticmethod
    def _analysis_prompt(formatted_papers, total):
        return (
            "你是一位严谨的学术研究分析师。请根据论文题录生成中文 Markdown 报告。\n"
            "报告必须包含：核心研究主题、研究方法与技术视角、关键创新与趋势、"
            "逐篇论文亮点、总体总结。逐篇亮点必须覆盖输入中的每篇论文，不得省略。\n"
            f"本次共分析 {total} 篇论文。\n\n{formatted_papers}"
        )

    @staticmethod
    def _synthesis_prompt(batch_results, total):
        return (
            "请把以下分批分析整合为一份中文 Markdown 综合报告。报告必须包含核心研究主题、"
            "研究方法与技术视角、关键创新与趋势、总体总结；保留所有批次中的逐篇论文亮点，"
            f"确保共覆盖 {total} 篇论文且不重复。\n\n"
            + "\n\n---\n\n".join(batch_results)
        )

    def execute(self, analysis_id):
        analysis = db.session.get(PaperAnalysis, analysis_id)
        if analysis is None:
            raise ValueError("分析任务不存在")
        analysis.status = "running"
        analysis.started_at = datetime.now(UTC)
        analysis.error_message = None
        db.session.commit()

        results = []
        generation = None
        for batch in self._batches(analysis.items):
            prompt = self._analysis_prompt("\n\n".join(text for _, text in batch), len(analysis.items))
            generation = self.llm_service.generate_text(
                "paper_analysis", prompt, profile_id=analysis.profile_id
            )
            results.append(generation.text)
        if len(results) > 1:
            generation = self.llm_service.generate_text(
                "paper_analysis",
                self._synthesis_prompt(results, len(analysis.items)),
                profile_id=analysis.profile_id,
            )
        markdown = generation.text if generation else ""
        if not markdown.strip():
            raise ValueError("模型返回了空分析结果")

        analysis.profile_id = generation.profile_id
        analysis.model_name = generation.model_name
        analysis.content_markdown = markdown.strip()
        analysis.status = "completed"
        analysis.finished_at = datetime.now(UTC)
        db.session.commit()
        analysis.artifact_md_path = self._write_artifact(analysis)
        db.session.commit()
        db.session.refresh(analysis)
        return analysis

    @staticmethod
    def fail(analysis_id, exc):
        analysis = db.session.get(PaperAnalysis, analysis_id)
        if analysis is None:
            return
        analysis.status = "failed"
        analysis.error_message = str(exc)
        analysis.finished_at = datetime.now(UTC)
        db.session.commit()

    @staticmethod
    def _write_artifact(analysis):
        configured = current_app.config.get("PAPER_ANALYSIS_ARTIFACT_ROOT")
        root = Path(configured) if configured else artifacts_root() / "paper-analysis"
        task_root = root / str(analysis.id)
        task_root.mkdir(parents=True, exist_ok=True)
        path = task_root / "analysis.md"
        path.write_text(analysis.content_markdown, encoding="utf-8")
        return str(path)
