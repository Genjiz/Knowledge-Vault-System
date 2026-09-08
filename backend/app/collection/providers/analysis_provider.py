import json

from app.collection.legacy import config as crawler_config
from app.collection.sources.base import ProviderError
from app.core.llm.service import LLMService


class AnalysisProvider:
    model_name = "gemini"

    def __init__(self, llm_service=None):
        self.llm_service = llm_service

    def _format_papers_for_prompt(self, papers):
        formatted_texts = []
        for index, paper in enumerate(papers, 1):
            keywords = paper.keywords_json
            if keywords:
                try:
                    keywords = ", ".join(json.loads(keywords))
                except json.JSONDecodeError:
                    pass
            else:
                keywords = ""

            lines = [
                f"Paper {index}",
                f"Title: {paper.title or 'N/A'}",
                f"Abstract: {paper.abstract or 'N/A'}",
                f"Keywords: {keywords}",
            ]
            if paper.title_zh:
                lines.append(f"Chinese Title: {paper.title_zh}")
            if paper.abstract_zh:
                lines.append(f"Chinese Abstract: {paper.abstract_zh}")
            formatted_texts.append("\n".join(lines))
        return "\n\n".join(formatted_texts)

    def generate_analysis(self, raw_issue, papers):
        prompt_template = crawler_config.get_prompt("journal_analysis")
        if not prompt_template:
            raise ProviderError("journal_analysis prompt is not configured")

        prompt = prompt_template.format(
            journal_name=raw_issue.journal_name,
            paper_count=len(papers),
        )
        prompt = f"{prompt}\n\n{self._format_papers_for_prompt(papers)}"

        try:
            result = (self.llm_service or LLMService()).generate_text("paper_analysis", prompt)
        except Exception as exc:
            raise ProviderError(f"Analysis request failed: {exc}") from exc
        self.model_name = result.model_name
        return result.text
