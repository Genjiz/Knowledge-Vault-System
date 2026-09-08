import json
import shutil

from dotenv import dotenv_values, set_key

from app.core.paths import workspace_root

SECRET_MAP_ENV = "LLM_API_KEYS_JSON"


class EnvSecretStore:
    """把模型密钥保存在不入库、不提交的根目录 .env。"""

    def __init__(self, env_path=None):
        self.env_path = env_path or workspace_root() / ".env"

    def _ensure_env_file(self):
        if self.env_path.exists():
            return
        example = workspace_root() / ".env.example"
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        if example.exists():
            shutil.copyfile(example, self.env_path)
        else:
            self.env_path.touch()

    def _values(self):
        if not self.env_path.exists():
            return {}
        raw = dotenv_values(self.env_path, encoding="utf-8").get(SECRET_MAP_ENV) or "{}"
        try:
            values = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return values if isinstance(values, dict) else {}

    def _write(self, values):
        self._ensure_env_file()
        serialized = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        set_key(
            str(self.env_path),
            SECRET_MAP_ENV,
            serialized,
            quote_mode="always",
            encoding="utf-8",
        )

    def get(self, profile_key):
        value = self._values().get(str(profile_key))
        return value.strip() if isinstance(value, str) and value.strip() else None

    def set(self, profile_key, api_key):
        values = self._values()
        values[str(profile_key)] = api_key.strip()
        self._write(values)

    def delete(self, profile_key):
        values = self._values()
        if str(profile_key) in values:
            values.pop(str(profile_key))
            self._write(values)
