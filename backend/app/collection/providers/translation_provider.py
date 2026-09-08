import json
from app.collection.sources.base import ProviderError
from app.core.llm.service import LLMService
from pydantic import BaseModel, ValidationError


class PaperTranslation(BaseModel):
    index: int
    title_zh: str = ""
    abstract_zh: str = ""


class IssueTranslation(BaseModel):
    papers: list[PaperTranslation]


class TranslationProvider:
    def __init__(self, client=None, model_name=None, llm_service=None):
        self.client = client
        self.model_name = model_name
        self.llm_service = llm_service

    def translate_papers(self, papers):
        papers_data = []
        for index, paper in enumerate(papers):
            papers_data.append(
                {
                    "index": index,
                    "title": paper.title if hasattr(paper, "title") else paper.get("title", ""),
                    "abstract": paper.abstract if hasattr(paper, "abstract") else paper.get("abstract", ""),
                }
            )

        prompt = (
            "你是一位严谨的学术翻译助手。请将以下论文标题与摘要翻译为简体中文。\n"
            "必须严格返回 JSON，且仅返回 JSON，不要附加任何解释文本。\n"
            "返回结构：{\"papers\": [{\"index\": int, \"title_zh\": str, \"abstract_zh\": str}]}\n"
            "要求：\n"
            "1) index 必须与输入一致；\n"
            "2) 对缺失内容返回空字符串；\n"
            "3) 保持学术术语准确、表达自然。\n\n"
            f"{json.dumps(papers_data, ensure_ascii=False, indent=2)}"
        )

        if self.client and self.model_name:
            # 保留旧构造器注入合同，供离线单元测试和渐进迁移使用。
            try:
                response_stream = self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt,
                    config=None,
                )
                parts = []
                for chunk in response_stream:
                    text = getattr(chunk, "text", None)
                    if not text and getattr(chunk, "candidates", None):
                        text = chunk.candidates[0].content.parts[0].text
                    if text:
                        parts.append(text)
                raw_response = "".join(parts)
            except Exception as exc:
                raise ProviderError(f"Translation request failed: {exc}") from exc
        else:
            try:
                result = (self.llm_service or LLMService()).generate_text(
                    "paper_translation", prompt
                )
                self.model_name = result.model_name
                raw_response = result.text
            except Exception as exc:
                raise ProviderError(f"Translation request failed: {exc}") from exc
        try:
            if hasattr(IssueTranslation, "model_validate_json"):
                parsed = IssueTranslation.model_validate_json(raw_response)
            else:
                parsed = IssueTranslation.parse_raw(raw_response)
        except ValidationError as exc:
            raise ProviderError(f"Translation schema validation failed: {exc}") from exc
        except Exception as exc:
            raise ProviderError(f"Translation parsing failed: {exc}") from exc

        translations = [{"title_zh": "", "abstract_zh": ""} for _ in papers_data]
        for item in parsed.papers:
            index = item.index
            if isinstance(index, int) and 0 <= index < len(translations):
                translations[index] = {
                    "title_zh": item.title_zh or "",
                    "abstract_zh": item.abstract_zh or "",
                }
        return translations
