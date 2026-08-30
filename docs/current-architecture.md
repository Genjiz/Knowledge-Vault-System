# Current Architecture

本文档记录已实现并经过验证的当前系统状态（简版，随系统演进更新）。目标态见 `docs/specifications/target-implementation-spec.md`。

## 技术栈

- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts + Tailwind CSS 4
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + google-genai
- 后端环境：仓库根目录 `.venv`（Python 3.11+）；前端依赖经 npm 安装

## 后端结构

应用入口：`backend/run.py` → `app.create_app()`（app factory + 蓝图注册）。

三个业务域当前的组织方式：

| 域 | 位置 | 组织方式 |
|---|---|---|
| 文献管理 | `app/models`、`app/routes`、`app/repositories` | 按层平铺 |
| 采集中心 | `app/crawler/`（models / repositories / services / providers / routes / runtime / legacy） | 按域分包 |
| 视频转笔记 | `app/video_notes/`（models / repositories / services / routes / runtime） | 按域分包 |

蓝图前缀：`/api/literatures`、`/api/tags`、`/api/folders`、`/api/notes`、`/api/backup`、`/api/crawl-tasks`、`/api/raw-issues`、`/api/video-note-tasks`、`/api/health`。

数据库结构由 Flask-Migrate（Alembic）管理，迁移脚本位于 `backend/migrations/`；`db.create_all()` 已从 app factory 移除（测试环境仍使用 create_all 建内存库）。现有库已 stamp 初始基线 `1100434363a6`。

## 数据与产物

运行数据统一位于 `backend/data/`（路径由 `app/core/paths.py` 唯一定义，可用环境变量 `DATA_ROOT` 整体重定向）：

- 主数据库：`backend/data/db/app.db`（SQLite）
- 上传文件：`backend/data/uploads/pdfs/`
- 采集产物：`backend/data/artifacts/crawler/raw-json/`（`ARTIFACT_ROOT`）
- 视频转笔记产物：`backend/data/artifacts/video-notes/<task_id>/`

采集核心表：`crawl_task`、`crawl_task_log`、`raw_issue`、`raw_paper`、`raw_issue_analysis`、`llm_run`。

原则：数据库是主存储；JSON/Markdown 是派生产物，用于重跑、审计、导出与复核。

## 运行时路径规则

- 运行数据目录统一由 `app/core/paths.py` 定义（`DATA_ROOT` 环境变量可整体重定向）；各目录保留独立环境变量覆盖（`DATABASE_URL`、`ARTIFACT_ROOT`、`UPLOAD_FOLDER`）。
- 运行时路径工具从代码位置向上查找同时包含 `backend/` 和 `frontend/` 的目录作为工作区根（`app/crawler/runtime/paths.py`）
- 浏览器 profile 目录：`.crawler-browser-profile/`（可用环境变量 `CRAWLER_BROWSER_DATA_ROOT` 覆盖）
- 采集历史脚本位于 `backend/app/crawler/legacy/`，由 provider 动态加载包装
- 浏览器可执行文件探测仅覆盖 Chrome/Chromium 常见路径，可用环境变量 `CRAWLER_BROWSER_PATH` 覆盖

## 当前限制

- 文献域按层平铺、采集与视频域按域分包，两种组织方式并存（待 PC 阶段重构统一）
- 视频转笔记后台任务使用裸 `threading.Thread`，无统一任务执行器（待 PE 阶段）
- 视频转笔记依赖系统级工具（conda 环境 `whisper`、`yt-dlp`、FFmpeg），未收敛到项目内依赖
- 采集数据与文献工作台数据尚未打通（待 PD 阶段）
