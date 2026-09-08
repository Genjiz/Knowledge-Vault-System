from app.collection.sources.base import ProviderError
from app.core.llm.service import LLMService


class NoteGenerationService:
    def __init__(self, client=None, model_name=None, llm_service=None):
        self.client = client
        self.model_name = model_name
        self.llm_service = llm_service

    @staticmethod
    def _format_generation_error(exc):
        message = str(exc)
        if "10060" in message or "timed out" in message.lower():
            return (
                "Gemini connection timed out. "
                "Check whether this machine can reach generativelanguage.googleapis.com:443 "
                "and configure GEMINI_PROXY_URL or HTTPS_PROXY/HTTP_PROXY if a proxy is required."
            )
        return message

    @staticmethod
    def _normalize_markdown(markdown):
        normalized = (markdown or "").strip()
        if not normalized:
            return ""

        fence = "```"
        first_fence = normalized.find(fence)
        if first_fence > 0:
            before_fence = normalized[:first_fence].strip()
            if before_fence:
                normalized = normalized[first_fence:]

        if normalized.startswith(fence):
            lines = normalized.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == fence:
                lines = lines[:-1]
            normalized = "\n".join(lines).strip()

        heading_index = normalized.find("\n# ")
        if heading_index >= 0:
            normalized = normalized[heading_index + 1 :].strip()
        elif normalized.startswith("# "):
            normalized = normalized.strip()

        return normalized

    def generate_note(self, *, transcript_text, source_url, bvid, video_title):
        prompt = (
            "我有一份 B 站视频的字幕文件（SRT 文本），请根据字幕内容生成一份结构化笔记。\n\n"
            "要求：\n"
            "1. 提炼视频的核心主题和要点\n"
            "2. 按逻辑章节整理内容\n"
            "3. 每个章节用简洁的语言概括关键信息\n"
            "4. 标注值得关注的重要细节或金句\n"
            "5. 最后给出一个简短总结\n"
            "6. 输出格式必须是 Markdown\n\n"
            f"视频标题：{video_title}\n"
            f"BVID：{bvid}\n"
            f"来源链接：{source_url}\n\n"
            "以下是字幕内容：\n"
            f"{transcript_text}"
        )

        if self.client and self.model_name:
            try:
                response_stream = self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt,
                )
                raw = "".join(
                    chunk.text for chunk in response_stream if getattr(chunk, "text", None)
                )
            except Exception as exc:
                raise ProviderError(
                    f"Note generation failed: {self._format_generation_error(exc)}"
                ) from exc
        else:
            try:
                result = (self.llm_service or LLMService()).generate_text("video_note", prompt)
                self.model_name = result.model_name
                raw = result.text
            except Exception as exc:
                raise ProviderError(
                    f"Note generation failed: {self._format_generation_error(exc)}"
                ) from exc

        markdown = self._normalize_markdown(raw)
        if not markdown:
            raise ProviderError("模型返回了空笔记")
        return markdown
