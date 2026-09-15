import os
from functools import lru_cache
from pathlib import Path


WORKSPACE_SENTINELS = ("backend", "frontend")


@lru_cache(maxsize=1)
def get_workspace_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if all((parent / part).exists() for part in WORKSPACE_SENTINELS):
            return parent
    raise RuntimeError("Unable to locate workspace root containing backend and frontend directories")


def get_project_root():
    return get_workspace_root()


def get_browser_data_root():
    override = os.environ.get("CRAWLER_BROWSER_DATA_ROOT")
    if override:
        return Path(override)
    return get_project_root() / ".crawler-browser-profile"


def get_legacy_crawler_root():
    return get_project_root() / "backend" / "app" / "collection" / "legacy"


def find_chrome_executable():
    candidates = [
        os.environ.get("CRAWLER_BROWSER_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Chromium\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def find_edge_executable():
    """查找普通 Edge；显式浏览器路径仅在确实指向 Edge 时复用。"""
    override = os.environ.get("CRAWLER_BROWSER_PATH")
    candidates = [
        override if override and Path(override).name.lower() == "msedge.exe" else None,
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None
