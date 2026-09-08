import importlib

from app.core.llm.errors import LLMError
from app.core.llm.gemini import load_gemini_proxy_url


class GeminiAdapter:
    def __init__(self, profile, api_key, client=None):
        self.profile = profile
        self.api_key = api_key
        self.client = client or self._create_client()

    def _create_client(self):
        try:
            genai = importlib.import_module("google.genai")
            genai_types = importlib.import_module("google.genai.types")
        except ModuleNotFoundError as exc:
            raise LLMError("google-genai is not installed") from exc

        options = {}
        if self.profile.base_url:
            options["base_url"] = self.profile.base_url
        proxy_url = load_gemini_proxy_url()
        if proxy_url:
            options["client_args"] = {"proxy": proxy_url, "trust_env": False}
            options["async_client_args"] = {"proxy": proxy_url, "trust_env": False}
        http_options = genai_types.HttpOptions(**options) if options else None
        return genai.Client(api_key=self.api_key, http_options=http_options)

    def generate_text(self, prompt):
        try:
            response = self.client.models.generate_content(
                model=self.profile.model_name,
                contents=prompt,
            )
        except Exception as exc:
            raise LLMError(f"Gemini request failed: {exc}") from exc
        text = getattr(response, "text", None)
        if not text:
            raise LLMError("Gemini returned an empty response")
        return text


class OpenAICompatibleAdapter:
    def __init__(self, profile, api_key, client=None):
        self.profile = profile
        self.api_key = api_key
        self.client = client or self._create_client()

    def _create_client(self):
        try:
            openai = importlib.import_module("openai")
        except ModuleNotFoundError as exc:
            raise LLMError("openai is not installed") from exc
        return openai.OpenAI(api_key=self.api_key, base_url=self.profile.base_url)

    def generate_text(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.profile.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc
        try:
            text = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMError("OpenAI-compatible response has an invalid shape") from exc
        if not text:
            raise LLMError("OpenAI-compatible model returned an empty response")
        return text


def create_adapter(profile, api_key):
    if profile.protocol == "gemini":
        return GeminiAdapter(profile, api_key)
    if profile.protocol == "openai":
        return OpenAICompatibleAdapter(profile, api_key)
    raise LLMError(f"Unsupported LLM protocol: {profile.protocol}")
