import importlib
import os
from functools import lru_cache

from dotenv import load_dotenv

from app.collection.sources.base import ProviderError
from app.collection.runtime.paths import get_project_root, get_workspace_root


def _env_file_candidates():
    workspace_root = get_workspace_root()
    project_root = get_project_root()

    candidates = []
    for path in (
        project_root / ".env",
        project_root / "backend" / ".env",
        workspace_root / ".env",
        workspace_root / "backend" / ".env",
    ):
        if path not in candidates:
            candidates.append(path)
    return candidates


@lru_cache(maxsize=1)
def load_runtime_env():
    for file_path in _env_file_candidates():
        if file_path.exists():
            load_dotenv(file_path, override=False, encoding="utf-8")


def load_gemini_api_key():
    load_runtime_env()
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key.strip()

    workspace_root = get_workspace_root()
    project_root = get_project_root()
    candidate_files = [
        project_root / "backend" / "gemini_api_key.txt",
        workspace_root / "gemini_api_key.txt",
    ]

    for file_path in candidate_files:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8").strip()

    raise ProviderError("Gemini API key not found")


def load_gemini_proxy_url():
    load_runtime_env()
    for env_name in ("GEMINI_PROXY_URL", "HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        value = os.environ.get(env_name)
        if value:
            return value.strip()
    return None


def create_gemini_client():
    try:
        genai = importlib.import_module("google.genai")
    except ModuleNotFoundError as exc:
        raise ProviderError("google-genai is not installed") from exc

    http_options = None
    proxy_url = load_gemini_proxy_url()
    if proxy_url:
        genai_types = importlib.import_module("google.genai.types")
        http_options = genai_types.HttpOptions(
            clientArgs={"proxy": proxy_url, "trust_env": False},
            asyncClientArgs={"proxy": proxy_url, "trust_env": False},
        )

    return genai.Client(api_key=load_gemini_api_key(), http_options=http_options)
