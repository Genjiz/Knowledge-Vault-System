"""运行数据路径的唯一权威定义。

除本模块外，代码不得硬编码数据目录字面量。所有数据目录可通过环境变量 DATA_ROOT
整体重定向（用于测试隔离或数据搬迁）。各目录仍保留独立环境变量覆盖，优先级最高。
"""
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def workspace_root() -> Path:
    return BACKEND_ROOT.parent


def data_root() -> Path:
    override = os.environ.get("DATA_ROOT")
    if override:
        return Path(override)
    return BACKEND_ROOT / "data"


def database_path() -> Path:
    return data_root() / "db" / "app.db"


def database_uri() -> str:
    return "sqlite:///" + database_path().as_posix()


def upload_folder() -> Path:
    return data_root() / "uploads" / "pdfs"


def artifacts_root() -> Path:
    return data_root() / "artifacts"


def literature_text_assets_root() -> Path:
    return artifacts_root() / "literature-text"


def crawler_artifacts_root() -> Path:
    return artifacts_root() / "crawler"
