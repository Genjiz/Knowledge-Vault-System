# Current Architecture

本文档记录已实现并经过验证的当前系统状态（简版，随系统演进更新）。目标态见 `docs/specifications/target-implementation-spec.md`。

## 技术栈

- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts + Tailwind CSS 4
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + google-genai
- 后端环境：仓库根目录 `.venv`（Python 3.11+）；前端依赖经 npm 安装

## 后端结构

应用入口：`backend/run.py` → `app.create_app()`（app factory + 蓝图注册）。

按功能分包（2026-08-30 重构后）：

| 包 | 职责 | 内部结构 |
|---|---|---|
| `app/core/` | 平台层：跨包公共设施 | extensions（db/cors/migrate）、paths（数据目录唯一权威）、response、errors（统一异常 + 全局错误处理器）、health、llm/（gemini.py + 多供应商注册表骨架） |
| `app/papers/` | 统一论文实体与文献工作台 | models（Literature/Tag/Folder/Note/Journal/JournalSourceConfig）、repositories、routes（/api/literatures /tags /folders /notes /backup）、services（paper_service：落库与合并） |
| `app/collection/` | 期刊采集管道 | models（CrawlTask/RawIssue/RawPaper 等）、repositories、services、routes（/api/crawl-tasks /raw-issues）、sources（SourceAdapter 接口 + NcpssdSource/ElsevierSource）、providers（analysis/translation LLM 适配）、pipeline（骨架）、runtime（浏览器/legacy 路径）、legacy（历史脚本隔离区） |
| `app/video_notes/` | 视频转笔记（独立功能） | models / repositories / services / routes / runtime |

依赖方向：`collection → papers → core`（单向），`video_notes → core`。

蓝图前缀：`/api/literatures`、`/api/tags`、`/api/folders`、`/api/notes`、`/api/backup`、`/api/crawl-tasks`、`/api/raw-issues`、`/api/journals`、`/api/video-note-tasks`、`/api/health`。

数据库结构由 Flask-Migrate（Alembic）管理，迁移脚本位于 `backend/migrations/`；`db.create_all()` 已从 app factory 移除（测试环境仍使用 create_all 建内存库）。已应用迁移：初始基线 `1100434363a6`、期刊与溯源 `c9b826cfa1c0`。

## 数据模型

- 统一论文实体：`literature`（题录 + 来源溯源 `source`(imported/collection)、`source_raw_paper_id`、`journal_id` 外键；`pdf_path` 可选，题录可无 PDF）
- 期刊一等实体：`journal`（name 唯一、issn、publisher）；`journal_source_config`（期刊-采集源配置，source_id 可选值 ncpssd/elsevier/cnki/official）
- 采集原始记录：`raw_issue`、`raw_paper`（保留为审计/重跑层，入库时向 `literature` upsert 合并）
- 采集核心表：`crawl_task`、`crawl_task_log`、`raw_issue_analysis`、`llm_run`

合并规则（T-4 打通）：按标题规范化（去除首尾/压缩空白、忽略大小写）去重；已存在只填充空字段（不覆盖用户数据），不存在则创建；采集来源论文带 `source=collection` 与 raw_paper 溯源 id，自动创建/关联 journal。

## 数据与产物

运行数据统一位于 `backend/data/`（路径由 `app/core/paths.py` 唯一定义，可用环境变量 `DATA_ROOT` 整体重定向）：

- 主数据库：`backend/data/db/app.db`（SQLite）
- 上传文件：`backend/data/uploads/pdfs/`
- 采集产物：`backend/data/artifacts/crawler/raw-json/`（`ARTIFACT_ROOT`）
- 视频转笔记产物：`backend/data/artifacts/video-notes/<task_id>/`

原则：数据库是主存储；JSON/Markdown 是派生产物，用于重跑、审计、导出与复核。

## 运行时路径规则

- 运行数据目录统一由 `app/core/paths.py` 定义（`DATA_ROOT` 环境变量可整体重定向）；各目录保留独立环境变量覆盖（`DATABASE_URL`、`ARTIFACT_ROOT`、`UPLOAD_FOLDER`）。
- 运行时路径工具从代码位置向上查找同时包含 `backend/` 和 `frontend/` 的目录作为工作区根（`app/collection/runtime/paths.py`）
- 浏览器 profile 目录：`.crawler-browser-profile/`（可用环境变量 `CRAWLER_BROWSER_DATA_ROOT` 覆盖）
- 采集历史脚本位于 `backend/app/collection/legacy/`，由 source 适配器动态加载包装
- 浏览器可执行文件探测仅覆盖 Chrome/Chromium 常见路径，可用环境变量 `CRAWLER_BROWSER_PATH` 覆盖

## 当前限制

- 文献工作台的 tag/folder/note/backup 业务逻辑仍在路由层（未下沉 service）
- 期刊筛选后端能力已就位（`/api/literatures?journal_id=`），前端筛选 UI 未接
- 采集任务为同步执行（请求内跑完）；如需异步化需改 API 契约并配合前端轮询（core/tasks 执行器已可用）
- 视频转笔记依赖系统级工具（conda 环境 `whisper`、`yt-dlp`、FFmpeg），未收敛到项目内依赖
- 采集源尚未实现 SourceAdapter 接口（现有 NcpssdSource/ElsevierSource 保留原实现，适配待 T-1 任务）
- PDF 采集（T-2）与采集源配置的前端界面未实现

## 后台任务执行器

`app/core/tasks.py` 提供统一 `TaskExecutor`（PE 阶段落地）：daemon 线程包装 + `submit(task_id, fn, on_error)` + `is_running/running_ids` 状态查询；异常经 `on_error(exc)` 回调由调用方落库。已接入：视频转笔记任务（提交时包装 app context，失败回调把任务标记为 failed 并写日志）。采集任务当前保持同步执行（见当前限制）。
