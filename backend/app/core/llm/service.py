from dataclasses import dataclass
from types import SimpleNamespace

from flask import current_app

from app.core.extensions import db
from app.core.llm.clients import create_adapter
from app.core.llm.errors import LLMError
from app.core.llm.gemini import load_gemini_api_key
from app.core.llm.models import LLMProfile, LLMSceneBinding
from app.core.llm.secrets import EnvSecretStore

SCENES = {
    "paper_analysis": "论文分析",
    "paper_translation": "论文翻译",
    "video_note": "视频笔记",
}

LEGACY_MODELS = {
    "paper_analysis": "gemini-3-flash-preview",
    "paper_translation": "gemini-3-flash-preview",
    "video_note": "gemini-2.5-flash",
}


@dataclass(frozen=True)
class GenerationResult:
    text: str
    profile_id: int | None
    model_name: str


class LLMService:
    def __init__(self, secret_store=None, adapter_factory=None):
        self.secret_store = secret_store or current_app.config.get("LLM_SECRET_STORE") or EnvSecretStore()
        self.adapter_factory = (
            adapter_factory or current_app.config.get("LLM_ADAPTER_FACTORY") or create_adapter
        )

    def _resolve_profile(self, scene, profile_id=None):
        if scene not in SCENES:
            raise LLMError(f"Unknown LLM scene: {scene}")
        if profile_id is not None:
            profile = db.session.get(LLMProfile, profile_id)
        else:
            binding = LLMSceneBinding.query.filter_by(scene=scene).first()
            profile = binding.profile if binding else None
        if profile is not None:
            if not profile.enabled:
                raise LLMError("Selected model profile is disabled")
            api_key = self.secret_store.get(profile.id)
            if not api_key and profile.protocol == "gemini":
                api_key = load_gemini_api_key()
            return profile, api_key

        # 兼容升级前的 Gemini 配置；正式库迁移后通常会命中持久化档案。
        profile = SimpleNamespace(
            id=None,
            protocol="gemini",
            base_url=None,
            model_name=LEGACY_MODELS[scene],
        )
        return profile, load_gemini_api_key()

    def generate_text(self, scene, prompt, profile_id=None):
        profile, api_key = self._resolve_profile(scene, profile_id)
        if not api_key:
            raise LLMError("API key is not configured for the selected model")
        adapter = self.adapter_factory(profile, api_key)
        text = adapter.generate_text(prompt)
        return GenerationResult(text=text, profile_id=profile.id, model_name=profile.model_name)

    def test_profile(self, profile):
        api_key = self.secret_store.get(profile.id)
        if not api_key and profile.protocol == "gemini":
            try:
                api_key = load_gemini_api_key()
            except Exception:
                api_key = None
        if not api_key:
            raise LLMError("API key is not configured for the selected model")
        adapter = self.adapter_factory(profile, api_key)
        return adapter.generate_text("请只回复 OK")
