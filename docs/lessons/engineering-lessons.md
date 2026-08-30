# Engineering Lessons

只记录已验证、可复用的工程经验。一次性调试过程和未经验证的猜测不写入。

## L-001 Windows 沙箱内 pip 需禁用缓存

- 日期：2026-08-30
- 现象：在本机沙箱环境中执行 `pip install` 时，pip 缓存目录写入 `AppData\Local\pip\cache` 触发 safe-delete 回收站错误（`windows-sandbox-recycle-bin-unavailable`），安装失败。
- 做法：统一使用 `pip install --no-cache-dir`。
- 适用范围：本机沙箱内执行的所有 pip 安装。

## L-002 .venv 含本机绝对路径，不可跨机器迁移

- 日期：2026-08-30
- 现象：Windows 下 `.venv` 内部的 `pyvenv.cfg` 与脚本记录绝对路径，复制到其他机器或盘符后失效。
- 做法：环境重建统一以 `backend/requirements.txt` 为准（`.venv\Scripts\python.exe -m pip install -r backend/requirements.txt`）；提交 `.venv` 仅为同机快照，跨机异常时重建而不是排障。
- 适用范围：所有 Python 环境迁移与重建场景。

## L-003 采集浏览器探测仅覆盖 Chrome/Chromium，Edge 需显式指定

- 日期：2026-08-30
- 现象：`app/crawler/runtime/paths.py` 的 `find_chrome_executable()` 只探测 Chrome/Chromium 常见安装路径；本机浏览器为 Edge（Chromium 内核，`msedge.exe` 不在探测列表）。
- 做法：需要使用 Edge 时，通过环境变量 `CRAWLER_BROWSER_PATH` 指定，或经用户确认后调整代码；不要假设 DrissionPage 能自动找到 Edge。
- 适用范围：采集中心所有浏览器自动化场景。
