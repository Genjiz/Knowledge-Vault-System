"""Knowledge Vault 桌面托盘启动器。

启动后不再出现任何终端窗口：前后端以无窗口子进程方式拉起，托盘图标常驻右下角，
关闭浏览器窗口不影响服务运行，右键退出时按进程树回收全部子进程。

端口由本文件统一分配并经由环境变量下发，前后端只消费结果，避免三处各自写死后
互相错位（详见 backend/app/core/ports.py）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
RUNTIME_DIR = ROOT_DIR / ".runtime"
LOG_DIR = RUNTIME_DIR / "logs"
PORTS_FILE = RUNTIME_DIR / "ports.json"

# 端口分配工具归属后端平台层，本文件不在包结构内，只能先把 backend 加入搜索路径。
sys.path.insert(0, str(BACKEND_DIR))
from app.core.ports import find_available_port  # noqa: E402

CREATE_NO_WINDOW = 0x08000000
BACKEND_PREFERRED_PORT = 5000
FRONTEND_PREFERRED_PORT = 3000
READY_TIMEOUT = 120
READY_INTERVAL = 0.5


def log(message: str) -> None:
    """pythonw 下没有控制台，输出同时落盘，便于事后排查。"""
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "launcher.log").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def http_ok(url: str, timeout: float = 2.0) -> bool:
    """本机回环探测必须绕开系统代理：用户配置 Clash 等代理后，回环请求若经代理
    转发，会因代理无法回连应用端口而误判服务未就绪。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def wait_until_ready(url: str, timeout: float = READY_TIMEOUT) -> bool:
    """轮询直到服务可响应。固定等待不可靠，后端冷启动耗时随环境波动。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if http_ok(url):
            return True
        time.sleep(READY_INTERVAL)
    return False


def open_in_browser(url: str) -> None:
    """用系统默认浏览器打开，不使用 Edge 应用模式（用户确认传统页面即可）。"""
    webbrowser.open(url)


class Services:
    """前后端进程的生命周期管理。"""

    def __init__(self) -> None:
        self.backend_port = 0
        self.frontend_port = 0
        self.state = "未启动"
        self._backend_proc: subprocess.Popen | None = None
        self._frontend_proc: subprocess.Popen | None = None
        self._log_handles: list = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.frontend_port}/"

    def start(self) -> None:
        self.state = "启动中"
        self.backend_port = find_available_port(BACKEND_PREFERRED_PORT)
        self.frontend_port = find_available_port(FRONTEND_PREFERRED_PORT)
        self._write_ports_file()
        log(f"分配端口：后端 {self.backend_port}，前端 {self.frontend_port}")

        self._backend_proc = self._spawn(
            [str(VENV_PYTHON), "run.py"],
            BACKEND_DIR,
            "backend.log",
            {"KV_BACKEND_PORT": str(self.backend_port)},
        )
        self._frontend_proc = self._spawn(
            "npm run dev",
            FRONTEND_DIR,
            "frontend.log",
            {
                "KV_BACKEND_PORT": str(self.backend_port),
                "KV_FRONTEND_PORT": str(self.frontend_port),
            },
            shell=True,
        )

        backend_health = f"http://127.0.0.1:{self.backend_port}/api/health"
        if not wait_until_ready(backend_health):
            raise RuntimeError(f"后端未就绪，请查看 {LOG_DIR / 'backend.log'}")
        if not wait_until_ready(self.url):
            raise RuntimeError(f"前端未就绪，请查看 {LOG_DIR / 'frontend.log'}")

        self.state = "运行中"

    def stop(self) -> None:
        self.state = "已停止"
        for proc in (self._frontend_proc, self._backend_proc):
            self._kill_tree(proc)
        self._frontend_proc = None
        self._backend_proc = None
        for handle in self._log_handles:
            try:
                handle.close()
            except OSError:
                pass
        self._log_handles.clear()
        self._remove_ports_file()

    def _spawn(self, args, cwd: Path, log_name: str, extra_env: dict, shell: bool = False):
        env = os.environ.copy()
        env.update(extra_env)
        env["PYTHONIOENCODING"] = "utf-8"

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # 句柄必须持有引用：子进程继承它，若被垃圾回收关闭，子进程写入即失败。
        handle = (LOG_DIR / log_name).open("w", encoding="utf-8", errors="replace")
        self._log_handles.append(handle)

        return subprocess.Popen(
            args,
            cwd=str(cwd),
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            shell=shell,
            creationflags=CREATE_NO_WINDOW,
        )

    @staticmethod
    def _kill_tree(proc) -> None:
        """按进程树回收。npm 及其派生的 node、vite 同属一棵树，逐个杀会漏。"""
        if proc is None or proc.poll() is not None:
            return
        subprocess.run(
            ["taskkill", "/f", "/t", "/pid", str(proc.pid)],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )

    def _write_ports_file(self) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        PORTS_FILE.write_text(
            json.dumps(
                {
                    "backend": self.backend_port,
                    "frontend": self.frontend_port,
                    "url": self.url,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _remove_ports_file(self) -> None:
        try:
            PORTS_FILE.unlink()
        except OSError:
            pass


def detect_existing_instance() -> dict | None:
    """端口文件存在且对应后端可响应，即认为已有实例在运行。"""
    if not PORTS_FILE.exists():
        return None
    try:
        data = json.loads(PORTS_FILE.read_text(encoding="utf-8"))
        backend_port = int(data["backend"])
    except Exception:
        return None
    if http_ok(f"http://127.0.0.1:{backend_port}/api/health"):
        return data
    return None


def build_icon_image():
    """运行时生成托盘图标，避免引入需要随包分发的图片资源。"""
    from PIL import Image, ImageDraw, ImageFont

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=14, fill=(37, 99, 235, 255))

    font = None
    for font_path in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, 28)
                break
            except OSError:
                font = None
    if font is None:
        font = ImageFont.load_default()

    text = "KV"
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )
    return image


def build_menu(services: Services, icon) -> "object":
    import pystray

    def on_open() -> None:
        open_in_browser(services.url)

    def on_restart() -> None:
        threading.Thread(target=restart_worker, args=(services, icon), daemon=True).start()

    # pystray 的 action 以 (icon, item) 两个参数被调用，无参 lambda 会在点击时报错。
    return pystray.Menu(
        pystray.MenuItem("打开界面", lambda icon, item: on_open(), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda item: f"状态：{services.state}", None, enabled=False),
        pystray.MenuItem(lambda item: f"前端：{services.frontend_port}", None, enabled=False),
        pystray.MenuItem(lambda item: f"后端：{services.backend_port}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("重启服务", lambda icon, item: on_restart()),
        pystray.MenuItem("退出", lambda icon, item: icon.stop()),
    )


def restart_worker(services: Services, icon) -> None:
    services.stop()
    try:
        services.start()
    except RuntimeError as exc:
        log(str(exc))
        icon.notify(str(exc), "Knowledge Vault 重启失败")
        return
    log(f"重启完成：{services.url}")
    icon.menu = build_menu(services, icon)
    open_in_browser(services.url)


def bootstrap(services: Services, icon) -> None:
    try:
        services.start()
    except RuntimeError as exc:
        log(str(exc))
        icon.notify(str(exc), "Knowledge Vault 启动失败")
        services.stop()
        return
    log(f"服务就绪：{services.url}")
    icon.menu = build_menu(services, icon)
    open_in_browser(services.url)


def main() -> int:
    if not VENV_PYTHON.exists():
        log(f"未找到虚拟环境解释器：{VENV_PYTHON}")
        return 1
    if not (FRONTEND_DIR / "node_modules").exists():
        log("前端依赖缺失，请先在 frontend/ 目录执行 npm install")
        return 1

    try:
        (LOG_DIR / "launcher.log").unlink()
    except OSError:
        pass

    existing = detect_existing_instance()
    if existing:
        log("检测到已有实例在运行，直接打开界面")
        open_in_browser(existing["url"])
        return 0

    try:
        import pystray
    except ImportError:
        log("缺少依赖 pystray，请执行 .venv\\Scripts\\python.exe -m pip install pystray Pillow")
        return 2

    services = Services()
    icon = pystray.Icon("knowledge-vault", build_icon_image(), "Knowledge Vault")
    icon.menu = build_menu(services, icon)

    # 关键：自定义 setup 会替换掉 pystray 默认的显示逻辑（默认 setup 仅做
    # icon.visible = True），必须在这里显式设为可见，否则图标注册了也永远隐身。
    def on_icon_ready(ready_icon) -> None:
        ready_icon.visible = True
        threading.Thread(target=bootstrap, args=(services, ready_icon), daemon=True).start()

    icon.run(setup=on_icon_ready)

    services.stop()
    log("已退出")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # pythonw 下异常无人可见，落盘后重抛，保证启动失败可排查。
        import traceback

        log(traceback.format_exc())
        raise
