import json

from app.crawler.legacy import config as crawler_config
from app.crawler.providers.base import ProviderError
from app.crawler.runtime.gemini_runtime import create_gemini_client


class AnalysisProvider:
    model_name = "gemini"

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
        client = create_gemini_client()

        self.model_name = crawler_config.get_default_model()
        prompt_template = crawler_config.get_prompt("journal_analysis")
        if not prompt_template:
            raise ProviderError("journal_analysis prompt is not configured")

        prompt = prompt_template.format(
            journal_name=raw_issue.journal_name,
            paper_count=len(papers),
        )
        prompt = f"{prompt}\n\n{self._format_papers_for_prompt(papers)}"

        try:
            response_stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
            )
        except Exception as exc:
            raise ProviderError(f"Failed to start analysis: {exc}") from exc

        full_response = []
        try:
            for chunk in response_stream:
                if getattr(chunk, "text", None):
                    full_response.append(chunk.text)
        except Exception as exc:
            raise ProviderError(f"Analysis streaming failed: {exc}") from exc

        return "".join(full_response)
