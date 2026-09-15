"""Elsevier API Key 的根目录 .env 存储。"""
import os
import shutil

from dotenv import dotenv_values, set_key, unset_key

from app.core.paths import workspace_root


class ElsevierKeyService:
    env_name = "ELSEVIER_API_KEY"

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

    def get(self):
        value = os.environ.get(self.env_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if not self.env_path.exists():
            return None
        value = dotenv_values(self.env_path, encoding="utf-8").get(self.env_name)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def set(self, api_key):
        value = str(api_key or "").strip()
        if not value:
            raise ValueError("API Key 不能为空")
        self._ensure_env_file()
        set_key(
            str(self.env_path),
            self.env_name,
            value,
            quote_mode="always",
            encoding="utf-8",
        )
        os.environ[self.env_name] = value

    def clear(self):
        if self.env_path.exists():
            unset_key(str(self.env_path), self.env_name, quote_mode="always")
        os.environ.pop(self.env_name, None)
