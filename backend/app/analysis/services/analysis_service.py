from datetime import UTC, datetime
from pathlib import Path

from flask import current_app
from sqlalchemy import or_

from app.analysis.models import PaperAnalysis, PaperAnalysisItem
from app.analysis.services.text_extraction_service import (
    LiteratureTextExtractionService,
    TextExtractionError,
)
from app.core.extensions import db
from app.core.llm.service import LLMService, require_enabled_profile
from app.core.paths import artifacts_root
from app.papers.models import Literature


PROMPT_TEMPLATE_VERSION = "paper-analysis-v1"
DEFAULT_PROMPT_TEMPLATE = (
    "你是一位严谨的学术研究分析师。请根据提供的论文题录与可用全文生成中文 Markdown 报告。\n"
    "报告必须包含：核心研究主题、研究方法与技术视角、关键创新与趋势、"
    "逐篇论文亮点、总体总结。逐篇亮点必须覆盖输入中的每篇论文，不得省略。"
)


class PaperAnalysisService:
    def __init__(self, llm_service=None, text_extraction_service=None, max_batch_chars=40000):
        self.llm_service = llm_service or LLMService()
        self.text_extraction_service = (
            text_extraction_service or LiteratureTextExtractionService()
        )
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
            query = Literature.query.filter(Literature.year == int(year))
            if number in ("year", "unassigned"):
                query = query.filter(
                    or_(
                        Literature.issue.is_(None),
                        Literature.issue == "",
                        Literature.issue.in_(("year", "unassigned")),
                    )
                )
            else:
                query = query.filter(Literature.issue == number)
            volume = str(issue.get("volume") or "").strip()
            if volume == "unknown":
                query = query.filter(
                    or_(
                        Literature.volume.is_(None),
                        Literature.volume == "",
                        Literature.volume == "unknown",
                    )
                )
            elif volume:
                query = query.filter(Literature.volume == volume)
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

    def create_analysis(
        self,
        *,
        literature_ids,
        issues,
        title=None,
        profile_id=None,
        custom_instruction=None,
        include_fulltext=False,
    ):
        profile = require_enabled_profile(profile_id)
        instruction = str(custom_instruction or "").strip()
        if len(instruction) > 10000:
            raise ValueError("自定义分析要求不能超过 10000 个字符")
        papers = self.select_literatures(literature_ids, issues)
        if not papers:
            raise ValueError("请至少选择一篇论文")
        analysis = PaperAnalysis(
            title=(title or "").strip() or self._default_title(papers),
            status="queued",
            profile_id=profile.id,
            paper_count=len(papers),
            prompt_template_version=PROMPT_TEMPLATE_VERSION,
            prompt_template_snapshot=DEFAULT_PROMPT_TEMPLATE,
            custom_instruction=instruction or None,
            include_fulltext=bool(include_fulltext),
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
        profile = require_enabled_profile(profile_id)
        analysis = PaperAnalysis(
            title=f"{source.title}（重新分析）",
            status="queued",
            profile_id=profile.id,
            paper_count=len(source.items),
            prompt_template_version=source.prompt_template_version,
            prompt_template_snapshot=source.prompt_template_snapshot,
            custom_instruction=source.custom_instruction,
            include_fulltext=source.include_fulltext,
            fulltext_count=source.fulltext_count,
            fulltext_failed_count=source.fulltext_failed_count,
            fulltext_error_message=source.fulltext_error_message,
        )
        db.session.add(analysis)
        db.session.flush()
        db.session.add_all([item.clone_for(analysis.id) for item in source.items])
        db.session.commit()
        db.session.refresh(analysis)
        return analysis

    @staticmethod
    def _default_title(papers):
        issues = {(paper.journal, paper.year, paper.volume, paper.issue) for paper in papers}
        if len(issues) == 1:
            journal, year, volume, issue = next(iter(issues))
            if journal and year and issue:
                volume_label = f" Vol.{volume}" if volume else ""
                return f"{journal} {year} 年{volume_label} 第 {issue} 期分析"
        return f"{len(papers)} 篇论文综合分析"

    def _format_item(self, item, index):
        parts = [
            f"Paper {index}",
            f"Title: {item.title or 'N/A'}",
            f"Authors: {item.authors or 'N/A'}",
            f"Journal: {item.journal or 'N/A'}",
            f"Year/Volume/Issue: {item.year or 'N/A'} / {item.volume or 'N/A'} / {item.issue or 'N/A'}",
            f"Abstract: {item.abstract or 'N/A'}",
            f"Keywords: {item.keywords or 'N/A'}",
        ]
        if item.text_asset is not None:
            parts.extend(
                [
                    "Full text Markdown:",
                    self.text_extraction_service.read_markdown(item.text_asset),
                ]
            )
        return "\n".join(parts)

    def _batches(self, items):
        batches, current, current_size = [], [], 0
        for index, item in enumerate(items, 1):
            text = self._format_item(item, index)
            continuation_prefix = f"Paper {index} (continued):\n"
            segment_limit = max(self.max_batch_chars - len(continuation_prefix), 1)
            for segment_index, segment in enumerate(self._split_text(text, segment_limit)):
                if segment_index:
                    segment = continuation_prefix + segment
                separator_size = 2 if current else 0
                if current and current_size + separator_size + len(segment) > self.max_batch_chars:
                    batches.append(current)
                    current, current_size = [], 0
                current.append((index, segment))
                current_size += (2 if current_size else 0) + len(segment)
        if current:
            batches.append(current)
        return batches

    @staticmethod
    def _split_text(text, limit):
        limit = max(int(limit), 1)
        if len(text) <= limit:
            return [text]
        segments = []
        remaining = text
        while remaining:
            if len(remaining) <= limit:
                segments.append(remaining)
                break
            split_at = remaining.rfind("\n\n", 0, limit + 1)
            if split_at < limit // 2:
                split_at = remaining.rfind("\n", 0, limit + 1)
            if split_at < limit // 2:
                split_at = limit
            segments.append(remaining[:split_at])
            remaining = remaining[split_at:]
        return segments

    @staticmethod
    def _analysis_prompt(
        formatted_papers,
        total,
        custom_instruction=None,
        prompt_template=None,
    ):
        custom = (
            f"\n\n用户补充分析要求：\n{custom_instruction.strip()}"
            if custom_instruction and custom_instruction.strip()
            else ""
        )
        return (
            f"{prompt_template or DEFAULT_PROMPT_TEMPLATE}{custom}\n"
            f"本次共分析 {total} 篇论文。\n\n{formatted_papers}"
        )

    @staticmethod
    def _synthesis_prompt(batch_results, total, custom_instruction=None):
        custom = (
            f"同时满足用户补充分析要求：{custom_instruction.strip()}。"
            if custom_instruction and custom_instruction.strip()
            else ""
        )
        return (
            "请把以下分批分析整合为一份中文 Markdown 综合报告。报告必须包含核心研究主题、"
            "研究方法与技术视角、关键创新与趋势、总体总结；保留所有批次中的逐篇论文亮点，"
            f"确保共覆盖 {total} 篇论文且不重复。{custom}\n\n"
            + "\n\n---\n\n".join(batch_results)
        )

    def _prepare_text_assets(self, analysis):
        included = 0
        failures = []
        if not analysis.include_fulltext:
            return included, failures
        for item in analysis.items:
            literature = item.literature
            if literature is None or not literature.pdf_path:
                continue
            try:
                item.text_asset = self.text_extraction_service.get_or_extract(literature)
                included += 1
            except TextExtractionError as exc:
                failures.append(f"{item.title}：{exc}")
        db.session.commit()
        return included, failures

    def execute(self, analysis_id):
        analysis = db.session.get(PaperAnalysis, analysis_id)
        if analysis is None:
            raise ValueError("分析任务不存在")
        analysis.status = "running"
        analysis.started_at = datetime.now(UTC)
        analysis.error_message = None
        db.session.commit()

        analysis.fulltext_count, fulltext_failures = self._prepare_text_assets(analysis)
        analysis.fulltext_failed_count = len(fulltext_failures)
        analysis.fulltext_error_message = (
            "\n".join(fulltext_failures) if fulltext_failures else None
        )
        db.session.commit()
        results = []
        generation = None
        for batch in self._batches(analysis.items):
            prompt = self._analysis_prompt(
                "\n\n".join(text for _, text in batch),
                len(analysis.items),
                analysis.custom_instruction,
                analysis.prompt_template_snapshot,
            )
            generation = self.llm_service.generate_text(
                "paper_analysis", prompt, profile_id=analysis.profile_id
            )
            results.append(generation.text)
        if len(results) > 1:
            generation = self.llm_service.generate_text(
                "paper_analysis",
                self._synthesis_prompt(results, len(analysis.items), analysis.custom_instruction),
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
