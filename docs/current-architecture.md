# Current Architecture

本文档记录已实现并经过验证的当前系统状态。目标态见 `docs/specifications/target-implementation-spec.md`。

## 技术栈

- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts + Tailwind CSS 4
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + google-genai
- 桌面启动器：pystray + Pillow（根目录 `desktop.py`，仅 Windows 使用）
- 后端环境：仓库根目录 `.venv`（Python 3.11+）；前端依赖经 npm 安装

## 后端结构

应用入口：`backend/run.py` → `app.create_app()`（app factory + 蓝图注册）。

按功能分包（2026-08-30 重构后）：

| 包 | 职责 | 内部结构 |
|---|---|---|
| `app/core/` | 平台层：跨包公共设施 | extensions（db/cors/migrate）、paths（数据目录唯一权威）、ports（端口分配唯一实现）、response、errors（统一异常 + 全局错误处理器）、health、llm/（gemini.py + 多供应商注册表骨架） |
| `app/papers/` | 统一论文实体与文献工作台 | models（Literature/Tag/Folder/Note/Journal/JournalSourceConfig）、repositories、routes（/api/literatures /tags /folders /notes /backup）、services（paper_service：落库与合并） |
| `app/collection/` | 期刊采集管道 | models（CrawlTask/RawIssue/RawPaper 等）、repositories、services（ingestion/translation/analysis/artifact/task/**source_runner**/**journal_seed**）、routes（/api/crawl-tasks /raw-issues /journals /collection）、sources（SourceAdapter 接口 + registry 注册表 + NcpssdSource/MagtechSource/ElsevierSource）、providers（analysis/translation LLM 适配）、pipeline（paper_merge 入库合并）、runtime（浏览器/legacy 路径）、legacy（历史脚本隔离区） |
| `app/video_notes/` | 视频转笔记（独立功能） | models / repositories / services / routes / runtime |

依赖方向：`collection → papers → core`（单向），`video_notes → core`。

蓝图前缀：`/api/literatures`、`/api/tags`、`/api/folders`、`/api/notes`、`/api/backup`、`/api/crawl-tasks`、`/api/raw-issues`、`/api/journals`、`/api/collection`、`/api/video-note-tasks`、`/api/health`。

数据库结构由 Flask-Migrate（Alembic）管理，迁移脚本位于 `backend/migrations/`；`db.create_all()` 已从 app factory 移除（测试环境仍使用 create_all 建内存库）。已应用迁移：初始基线 `1100434363a6`、期刊与溯源 `c9b826cfa1c0`、采集源身份统一 `a3f7c1d92e05`、期刊区域字段 `c4e2a9f81b37`。

## 数据模型

- 统一论文实体：`literature`（题录 + 来源溯源 `source`(imported/collection)、`source_raw_paper_id`、`journal_id` 外键；`pdf_path` 可选，题录可无 PDF）
- 期刊一等实体：`journal`（name 唯一、issn、publisher、region 区域为显式字段，决定可选源范围与论文语言语义）；`journal_source_config`（期刊-采集源配置，source_id 取自采集源注册表且区域须与期刊一致，含 enabled / is_default / config_json / 最近测试结果）
- 采集原始记录：`raw_issue`（source_type 存真实采集源 id + region 区域）、`raw_paper`（保留为审计/重跑层，含 doi，入库时向 `literature` upsert 合并）
- 采集核心表：`crawl_task`（source_type + region）、`crawl_task_log`、`raw_issue_analysis`、`llm_run`

合并规则（T-4 打通）：按标题规范化（去除首尾/压缩空白、忽略大小写）去重；已存在只填充空字段（不覆盖用户数据），不存在则创建；采集来源论文带 `source=collection` 与 raw_paper 溯源 id，自动创建/关联 journal。

## 采集源与期刊配置（T-1）

采集源注册表 `app/collection/sources/registry.py` 是 source_id 与采集源实现的唯一映射：

| source_id | 显示名 | region | 列期号 | 需要浏览器 | 期刊级配置 |
|---|---|---|---|---|---|
| `ncpssd` | 国家哲社文献中心 | domestic | 否 | 是 | 无（期刊 param 由 legacy 缓存解析） |
| `magtech` | 期刊官网（Magtech） | domestic | 是 | 否 | `base_url` |
| `elsevier` | Elsevier | foreign | 否 | 是 | 无（slug 由 legacy 配置解析） |

- 能力声明（`source_id` / `display_name` / `region` / `capabilities` / `config_fields`）定义在 `sources/base.py` 的 SourceAdapter 上；新增采集源只需实现接口并在注册表登记，全链路生效。
- `source_type` 在 `crawl_task` / `raw_issue` 中存真实 source_id；`region` 承担国内/国外语义，供语言推断与前端分组。
- 源动作（测试连接、探测期号）收口在 `services/source_runner.py`，路由层只依赖其调用契约，测试可整体注入替换（`app.config["JOURNAL_SOURCE_RUNNER"]`）。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/collection/sources` | 源注册表与能力清单 |
| GET | `/api/journals` | 期刊 + 已配置源 + 采集统计 |
| POST / PUT / DELETE | `/api/journals[/\<id\>]` | 期刊增删改 |
| PUT | `/api/journals/<id>/sources` | 批量提交该期刊全部源配置（未提交的源删除，至多一个默认源） |
| POST | `/api/journals/<id>/sources/<source_id>/test` | 测试源连通性，结果落库供列表展示 |
| GET | `/api/journals/<id>/issues?source_id=&year=` | 探测某年可用期号 |
| POST | `/api/journals/import-known` | 导入内置期刊清单（NCPSSD 收录 + 已知官网源），只补不覆盖 |

期刊初始数据由 `services/journal_seed.py` 播种（NCPSSD 收录的国内期刊 + 情报学报官网源 + IP&M 的 Elsevier 源），之后由「期刊与采集源」页面维护；期刊区域是用户维护的显式字段，采集源按区域与期刊匹配，配置接口会拒绝区域不符的源。

Magtech 官网源走纯 HTTP 结构化导出（同类站点可复用 `base_url` 配置接入）：年页 `showTenYearVolumnDetail.do?nian={year}` → 期页 `volumn_{id}.shtml` → 文章 id → `getTxtFile.do?fileType=BibTeX`（题录/关键词/DOI）与 `fileType=EndNote`（摘要），每篇 2 个请求，无需浏览器。已实测：情报学报 2026 年第 7 期采集 10 篇题录，标题/作者/摘要/关键词/DOI/页码齐备，并自动合并进 `literature`（`source=collection`）。

「测试连接」是轻量探测，不采集论文、不落临时文件：`magtech` 请求年页解析期号并回报识别结果；`ncpssd` 校验期刊定位参数是否已缓存 + 站点探活；`elsevier` 校验期刊 slug 是否已配置 + 站点探活。仅测试结果状态会写入 `journal_source_config`。

## 前端页面

| 路由 | 页面 | 职责 |
|---|---|---|
| `/crawler/journals` | 期刊与采集源 | 新增/编辑期刊（含区域）、配置该期刊可用源（按区域过滤）、测试连接、查看采集统计；不发起采集 |
| `/crawler/tasks` | 采集任务台 | 选期刊 → 选源（仅该期刊已启用源）→ 选年 → 探测期号 → 发起采集；不维护期刊与源 |

两页靠链接互相跳转：期刊未配置可用源时采集台禁用提交并给出跳转入口。

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

## 启动方式与端口管理

- 推荐入口：根目录 `desktop.bat` → 无窗口拉起 `desktop.py`（pythonw）。启动器负责：单实例检测（`.runtime/ports.json` + 健康检查）、端口分配、后台拉起前后端（`CREATE_NO_WINDOW`，日志落 `.runtime/logs/`）、轮询 `/api/health` 就绪后用系统默认浏览器打开界面、托盘常驻（打开界面/重启服务/退出），退出按进程树 `taskkill /f /t` 回收。
- 备用入口：`start.bat` / `stop.bat`（终端窗口方式，按固定端口 kill）。
- 端口规则：决策收口在启动器，经环境变量下发——`KV_BACKEND_PORT` → `backend/run.py`，`KV_BACKEND_PORT`/`KV_FRONTEND_PORT` → `frontend/vite.config.js`。策略为首选端口（5000/3000）+ 自动顺延；显式注入的端口被占时报错，未注入时自动顺延。`app/core/ports.py` 是端口分配的唯一实现。
- 后端默认关闭 Flask 调试 reloader（`FLASK_DEBUG=1` 可开启）；Vite 显式绑定 `127.0.0.1`，启动器注入端口时启用 `strictPort`。
- 端口记录与进程日志位于 `.runtime/`（不提交），退出后删除端口记录文件。

## 当前限制

- 文献工作台的 tag/folder/note/backup 业务逻辑仍在路由层（未下沉 service）
- 期刊筛选后端能力已就位（`/api/literatures?journal_id=`），前端筛选 UI 未接
- 采集任务为同步执行（请求内跑完）；如需异步化需改 API 契约并配合前端轮询（core/tasks 执行器已可用）
- 视频转笔记依赖系统级工具（conda 环境 `whisper`、`yt-dlp`、FFmpeg），未收敛到项目内依赖
- 全文 PDF 采集（T-2）未实现：`MagtechSource.download_pdf` 只返回直链，下载与落盘待接
- Magtech 年页 `showTenYearVolumnDetail.do` 仅覆盖近十年，更早年份的期号探测未实现
- 官网源只取中文题录，英文标题/摘要需解析摘要页 HTML，未实现

## 后台任务执行器

`app/core/tasks.py` 提供统一 `TaskExecutor`（PE 阶段落地）：daemon 线程包装 + `submit(task_id, fn, on_error)` + `is_running/running_ids` 状态查询；异常经 `on_error(exc)` 回调由调用方落库。已接入：视频转笔记任务（提交时包装 app context，失败回调把任务标记为 failed 并写日志）。采集任务当前保持同步执行（见当前限制）。

## 测试组织

`backend/tests/` 按包归位：`core/`（路径、任务执行器、bootstrap、health、gemini）、`papers/`（模型、合并、文献 API）、`collection/`（采集各服务/源/工作流、期刊与源 API、能力声明与注册表、播种）、`video_notes/`（视频模块）。测试临时目录统一在 OS 临时目录 `knowledge-vault-tests/` 下（规避 safe-delete 守卫，见 lessons L-004）。外部服务（Gemini、真实站点、浏览器）调用一律用 mock / fixture 离线覆盖（遵循 `AGENTS.md` 7.2）；确需真实调用时，把 `DATA_ROOT` 重定向到临时库副本再验证，不写正式运行数据（见 lessons L-011）。全量套件 150 个测试。
