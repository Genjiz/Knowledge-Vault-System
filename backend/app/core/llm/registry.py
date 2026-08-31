"""多模型供应商注册表（T-7 骨架）。

本期仅提供配置结构与注册接口，未接入实际调用。环境变量约定（后续落地）：
LLM_<PROVIDER_ID>_BASE_URL / _API_KEY / _MODEL（可选 _API_STYLE）。
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderConfig:
    id: str
    base_url: str
    api_key: str
    model: str
    api_style: str = "openai"  # openai | gemini


_REGISTRY: dict[str, ProviderConfig] = {}


def register_provider(config: ProviderConfig) -> None:
    _REGISTRY[config.id] = config


def get_provider(provider_id: str) -> Optional[ProviderConfig]:
    return _REGISTRY.get(provider_id)


def list_providers() -> dict[str, ProviderConfig]:
    return dict(_REGISTRY)
