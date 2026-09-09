# Current Architecture

本文档记录已实现并经过验证的当前系统状态。目标态见 `docs/specifications/target-implementation-spec.md`。

## 技术栈

- 前端：React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + TanStack Router + TanStack Query + React Hook Form + Zod + Axios + ECharts
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + google-genai + openai
- 桌面启动器：pystray + Pillow（根目录 `desktop.py`，仅 Windows 使用）
- 后端环境：仓库根目录 `.venv`（Python 3.11+）；前端使用 Node.js `^20.19.0` 或 `>=22.12.0`，依赖经 npm 安装

## 后端结构

应用入口：`backend/run.py` → `app.create_app()`（app factory + 蓝图注册）。

按功能分包（2026-08-30 重构后）：

| 包 | 职责 | 内部结构 |
|---|---|---|
| `app/core/` | 平台层：跨包公共设施 | extensions（db/cors/migrate）、paths（数据目录唯一权威）、ports（端口分配唯一实现）、response、errors、health、tasks、llm/（模型档案、场景绑定、密钥存储、Gemini/OpenAI 适配器与 API） |
| `app/papers/` | 统一论文实体、文献工作台与论文分析 | models（Literature/Tag/Folder/Note/Journal/JournalSourceConfig/PaperAnalysis）、repositories、routes（/api/literatures /paper-analyses /tags /folders /notes /backup）、services（论文合并与分析编排） |
| `app/collection/` | 期刊采集管道 | models（CrawlTask/RawIssue/RawPaper/LiteratureSource/FullTextTask 等）、repositories、services（ingestion/translation/analysis/artifact/task/**source_runner**/**raw_issue**/**fulltext**）、routes（/api/crawl-tasks /raw-issues /fulltext-tasks /journals /collection）、sources（SourceAdapter 接口 + registry 注册表 + NcpssdSource/MagtechSource/ElsevierSource）、providers（兼容旧期号流程的 LLM 适配）、pipeline（paper_merge 多来源关联与字段物化）、runtime（浏览器/legacy 路径）、legacy（历史脚本隔离区） |
| `app/video_notes/` | 视频转笔记（独立功能） | models / repositories / services / routes / runtime |

依赖方向：`collection → papers → core`（单向），`video_notes → core`。

蓝图前缀：`/api/literatures`、`/api/paper-analyses`、`/api/llm`、`/api/tags`、`/api/folders`、`/api/notes`、`/api/backup`、`/api/crawl-tasks`、`/api/raw-issues`、`/api/fulltext-tasks`、`/api/journals`、`/api/collection`、`/api/video-note-tasks`、`/api/health`。

数据库结构由 Flask-Migrate（Alembic）管理，迁移脚本位于 `backend/migrations/`；`db.create_all()` 已从 app factory 移除（测试环境仍使用 create_all 建内存库）。已应用迁移：初始基线 `1100434363a6`、期刊与溯源 `c9b826cfa1c0`、采集源身份统一 `a3f7c1d92e05`、期刊区域字段 `c4e2a9f81b37`、多来源文献溯源 `d7b9e4a12f60`、Magtech 全文采集 `e84f3c9a61b2`、模型平台与论文分析 `5703b05951aa`、期号预期篇数与 Magtech URL 修复 `f6a1c2d3e4b5`。

## 数据模型

- 统一论文实体：`literature`（题录 + `journal_id`；`user_edited_fields_json` 记录人工保护字段，`field_sources_json` 记录当前各字段来源；旧字段 `source` / `source_raw_paper_id` 保留兼容；`pdf_path` 可选，`pdf_source_type` / `pdf_source_raw_paper_id` / `pdf_sha256` / `pdf_size_bytes` 记录当前 PDF 来源与文件元数据）
- 期刊一等实体：`journal`（name 唯一、issn、publisher、region 区域为显式字段，决定可选源范围与论文语言语义）；`journal_source_config`（期刊-采集源配置，source_id 取自采集源注册表且区域须与期刊一致，含 enabled / is_default / config_json / 最近测试结果）
- 采集原始记录：`raw_issue`（source_type 存真实采集源 id + region 区域；`expected_paper_count` 保存来源报告的应有篇数，缺失或非法时回退到本次采集篇数；API 另按非空题名、非空摘要和关联文献 PDF 实时返回三项完成数）、`raw_paper`（保留为审计/重跑层，含 doi 与 `source_ref_json` 稳定源引用，入库时向 `literature` upsert 合并；API 同时返回关联统一文献 id 与 PDF 路径）
- 多来源关联：`literature_source`（一条 raw_paper 只关联一条 literature，一条 literature 可关联多个来源；删除 raw_paper 时级联删除关联）
- 采集核心表：`crawl_task`（source_type + region）、`crawl_task_log`、`raw_issue_analysis`、`llm_run`
- 模型平台：`llm_profile` 保存协议、Base URL、模型名、启用状态和测试结果；`llm_scene_binding` 为论文分析、论文翻译、视频笔记绑定默认模型。API Key 不入库。
- 论文分析：`paper_analysis` 保存异步任务、模型和 Markdown 结果；`paper_analysis_item` 保存每篇统一文献的输入快照，原文献删除后快照仍保留。
- 全文任务：`fulltext_task` 记录 single / issue / after_ingestion 任务总览，`fulltext_task_item` 记录逐篇成功、失败、跳过状态及下载来源快照

合并规则（T-4）：DOI 非空时优先按 DOI 匹配，否则按清洗后的标题 + 期刊 + 年份 + 期号匹配。统一文献字段按 `用户编辑 > magtech > ncpssd > 其他来源` 逐字段选择首个非空值，因此一条文献可以混合多个来源字段；人工编辑字段不会被采集覆盖。删除或重采期号后自动从剩余来源重新物化；最后一个来源删除时保留文献及其当前字段，并把非人工字段来源标记为 `retained`。`source_raw_paper_id` 指向当前最高优先级关联，仅用于旧代码兼容。

## 采集源与期刊配置（T-1）

采集源注册表 `app/collection/sources/registry.py` 是 source_id 与采集源实现的唯一映射：

| source_id | 显示名 | region | 列期号 | 需要浏览器 | 期刊级配置 |
|---|---|---|---|---|---|
| `ncpssd` | 国家哲社文献中心 | domestic | 否 | 是 | 无（期刊 param 由 legacy 缓存解析） |
| `magtech` | 期刊官网（Magtech） | domestic | 是 | 否 | `base_url`；支持全文 PDF |
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
| DELETE | `/api/raw-issues/<id>` | 删除指定来源的采集期号、原始论文和派生产物；保留统一文献并按剩余来源回算 |
| POST | `/api/literatures/<id>/fulltext-tasks` | 单篇获取全文；`replace_existing=true` 只允许替换已有 Magtech PDF |
| POST | `/api/raw-issues/<id>/fulltext-tasks` | 为一个 Magtech 期号批量补采缺失全文 |
| GET | `/api/fulltext-tasks[/<id>]` | 查询全文任务总览和逐篇结果，可按文献或期号过滤 |

系统不再内置或自动导入期刊清单；新数据库的期刊为空，由「期刊与采集源」页面维护。期刊区域是用户维护的显式字段，采集源按区域与期刊匹配，配置接口会拒绝区域不符的源。

## 模型平台与论文分析

- `/settings/models` 管理多个 Gemini Native / OpenAI Compatible 模型档案及三个场景默认值；连接测试只返回状态，API Key 永不回传。
- 非敏感模型配置存 SQLite；页面保存的 Key 以 JSON 映射写入根目录 `.env` 的 `LLM_API_KEYS_JSON`。已迁移的 Gemini 档案在未配置专属 Key 时兼容读取 `GEMINI_API_KEY` 或历史 Key 文件。
- Gemini `base_url` 可空（使用官方地址），OpenAI Compatible 必须显式提供 API 根地址；业务服务统一调用 `LLMService.generate_text`。
- 后端 CORS 只允许 `127.0.0.1` / `localhost` 的 HTTP 端口来源，防止外部网页修改 Base URL 后借后端发送本机密钥。
- `/paper-analysis` 支持按单期、多期或多篇论文选择；期号按统一文献的期刊文本、年份、期号展开，采集与手工导入论文按 `literature_id` 去重。
- 分析任务由 `TaskExecutor` 异步运行，按输入字符数在论文边界分批；多批结果再次综合并落库，同时写入 `backend/data/artifacts/paper-analysis/<task_id>/analysis.md`。

Magtech 官网源走纯 HTTP 结构化导出（同类站点可复用 `base_url` 配置接入）：年页 `showTenYearVolumnDetail.do?nian={year}` → 期页 `volumn_{id}.shtml` → 文章 id → `getTxtFile.do?fileType=BibTeX`（题录/关键词/DOI）与 `fileType=EndNote`（摘要），每篇 2 个请求，无需浏览器。论文外部页按文章 id 固定生成 `/CN/abstract/abstract{id}.shtml`，不采用 BibTeX 中可能落入软 404 的 `/CN/abstract/article_{id}.shtml`；迁移同时规范化已有原始论文和统一文献 URL。标题中的 `bold` / `italic` / `sup` / `sub` 仅在标签严格成对且正确嵌套时清除；未配对、错误嵌套或未知标签保留原文并记录 warning。全文使用稳定 article_id 请求 `downloadArticleFile.do?attachType=PDF&id=<article_id>`；响应需以 `%PDF-` 开头且不超过 100 MB，验证后通过同目录临时文件原子替换。已实测情报学报官网 PDF 接口返回有效 `%PDF-1.4` 文件。

全文采集与题录合并相互独立：采集台可勾选题录完成后补采全文，但后台仍先同步完成题录，再创建异步全文任务；PDF 失败不回滚题录。批量任务跳过已有 PDF；用户上传 PDF 永不被自动覆盖；单篇重新获取只能替换当前 Magtech PDF。同一期号删除或重采时保留已下载 PDF，只把失效的 raw_paper 引用置空。

「测试连接」是轻量探测，不采集论文、不落临时文件：`magtech` 请求年页解析期号并回报识别结果；`ncpssd` 校验期刊定位参数是否已缓存 + 站点探活；`elsevier` 校验期刊 slug 是否已配置 + 站点探活。仅测试结果状态会写入 `journal_source_config`。

## 前端结构与页面

入口为 `frontend/src/main.tsx`，应用壳与路由位于 `src/app/`。`AppShell` 提供 Workspace / Collection / Media / System / Utilities 五组导航；TanStack Router 按业务域懒加载页面；TanStack Query 管理服务端数据与后台任务轮询。

- `src/api/`：Axios client、统一响应信封与错误模型、TypeScript API 合同；数组查询参数按重复 key 序列化。
- `src/components/`：基于原生元素与 Radix primitives 的源码组件，以及按需注册模块的 ECharts 封装。
- `src/features/`：按 dashboard、literatures、analysis、settings、organize、utilities、collection、video 划分页面与业务逻辑。
- 文献表单使用 React Hook Form + Zod；论文分析 Markdown 经过本地安全解析后渲染；普通笔记仍使用文本输入，不引入富文本编辑器。
- Tailwind CSS 4 由 Vite 插件接入，组件视觉规则保留在 `src/index.css`；生产构建按业务域拆包，`scripts/check-chunk-sizes.mjs` 强制活动 JavaScript chunk 不超过 500 KiB。

| 路由组 | 页面 |
|---|---|
| `/`、`/statistics` | 仪表盘、统计分析 |
| `/literatures`、`/literatures/new`、`/literatures/<id>`、`/literatures/<id>/edit` | 文献列表、创建、详情与编辑 |
| `/paper-analysis` | 单期、多期或多篇论文分析、任务历史与结果 |
| `/tags`、`/folders` | 标签与文件夹管理 |
| `/import`、`/backup` | 导入、备份与恢复 |
| `/crawler/journals`、`/crawler/tasks` | 期刊与采集源配置、采集任务台 |
| `/crawler/issues`、`/crawler/issues/<id>` | 原始期号库与详情、翻译及论文分析跳转 |
| `/video-notes`、`/video-notes/tasks`、`/video-notes/tasks/<id>` | 视频任务创建、列表、状态、日志与产物 |
| `/settings/models` | 模型档案、连接测试与场景默认模型 |

期刊与采集源页面不发起采集；采集任务台只使用该期刊已启用的源。两页靠链接互相跳转，期刊未配置可用源时采集台禁用提交并给出配置入口。Magtech 题录采集可勾选完成后补采全文；期号库独立展示应有篇数，标题、摘要和全文并列显示「已采集数/应有数」及按比例填充的彩色进度线，不为国内期刊显示无操作价值的翻译状态。期号库和详情提供次级样式的「分析本期」快捷入口，模型生成操作统一在论文分析页执行；期号详情的论文展开项可打开期刊原文页，关联文献存在本地 PDF 时可直接阅读全文。文献详情可单篇获取/重新获取 Magtech PDF，并展示题录字段来源、PDF 来源和全文任务状态。

## 数据与产物

运行数据统一位于 `backend/data/`（路径由 `app/core/paths.py` 唯一定义，可用环境变量 `DATA_ROOT` 整体重定向）：

- 主数据库：`backend/data/db/app.db`（SQLite）
- 上传文件：`backend/data/uploads/pdfs/`
- 采集产物：`backend/data/artifacts/crawler/raw-json/`（`ARTIFACT_ROOT`）
- 视频转笔记产物：`backend/data/artifacts/video-notes/<task_id>/`
- 论文分析产物：`backend/data/artifacts/paper-analysis/<task_id>/analysis.md`

原则：数据库是主存储；JSON/Markdown 是派生产物，用于重跑、审计、导出与复核。

## 运行时路径规则

- 运行数据目录统一由 `app/core/paths.py` 定义（`DATA_ROOT` 环境变量可整体重定向）；各目录保留独立环境变量覆盖（`DATABASE_URL`、`ARTIFACT_ROOT`、`UPLOAD_FOLDER`）。
- 运行时路径工具从代码位置向上查找同时包含 `backend/` 和 `frontend/` 的目录作为工作区根（`app/collection/runtime/paths.py`）
- 浏览器 profile 目录：`.crawler-browser-profile/`（可用环境变量 `CRAWLER_BROWSER_DATA_ROOT` 覆盖）
- 采集历史脚本位于 `backend/app/collection/legacy/`，由 source 适配器动态加载包装
- 浏览器可执行文件探测仅覆盖 Chrome/Chromium 常见路径，可用环境变量 `CRAWLER_BROWSER_PATH` 覆盖
- 模型 API Key 映射位于根目录 `.env` 的 `LLM_API_KEYS_JSON`（不提交）；数据库只存非敏感模型配置。

## 启动方式与端口管理

- 推荐入口：根目录 `desktop.bat` → 无窗口拉起 `desktop.py`（pythonw）。启动器负责：单实例检测（`.runtime/ports.json` + 健康检查）、端口分配、后台拉起前后端（`CREATE_NO_WINDOW`，日志落 `.runtime/logs/`）、轮询 `/api/health` 就绪后用系统默认浏览器打开界面、托盘常驻（打开界面/重启服务/退出），退出按进程树 `taskkill /f /t` 回收。
- 备用入口：`start.bat` / `stop.bat`（终端窗口方式，按固定端口 kill）。
- 端口规则：决策收口在启动器，经环境变量下发——`KV_BACKEND_PORT` → `backend/run.py`，`KV_BACKEND_PORT`/`KV_FRONTEND_PORT` → `frontend/vite.config.ts`。策略为首选端口（5000/3000）+ 自动顺延；显式注入的端口被占时报错，未注入时自动顺延。`app/core/ports.py` 是端口分配的唯一实现。
- 后端默认关闭 Flask 调试 reloader（`FLASK_DEBUG=1` 可开启）；Vite 显式绑定 `127.0.0.1`，启动器注入端口时启用 `strictPort`。
- 端口记录与进程日志位于 `.runtime/`（不提交），退出后删除端口记录文件。

## 当前限制

- 文献工作台的 tag/folder/note/backup 业务逻辑仍在路由层（未下沉 service）
- 期刊筛选后端能力已就位（`/api/literatures?journal_id=`），前端筛选 UI 未接
- 采集任务为同步执行（请求内跑完）；如需异步化需改 API 契约并配合前端轮询（core/tasks 执行器已可用）
- 视频转笔记依赖系统级工具（conda 环境 `whisper`、`yt-dlp`、FFmpeg），未收敛到项目内依赖
- 全文自动采集目前只支持已配置的国内 Magtech 期刊官网；NCPSSD、Elsevier、其他国外来源及需登录/付费/验证码的页面不支持，也不绕过访问控制
- 全文任务由进程内 daemon 线程执行，应用重启不会自动恢复未完成任务
- 论文分析任务同样由进程内 daemon 线程执行，应用重启不会自动恢复未完成任务，可从历史记录重新分析
- Magtech 年页 `showTenYearVolumnDetail.do` 仅覆盖近十年，更早年份的期号探测未实现
- 官网源只取中文题录，英文标题/摘要需解析摘要页 HTML，未实现

## 后台任务执行器

`app/core/tasks.py` 提供统一 `TaskExecutor`（PE 阶段落地）：daemon 线程包装 + `submit(task_id, fn, on_error)` + `is_running/running_ids` 状态查询；异常经 `on_error(exc)` 回调由调用方落库。已接入：视频转笔记、全文下载和论文分析任务（均包装 app context，失败回调落库）。题录采集任务仍保持请求内同步执行，题录后的全文下载是独立异步阶段。

## 测试组织

`backend/tests/` 按包归位：`core/`（路径、任务执行器、bootstrap、health、Gemini、多模型平台）、`papers/`（模型、多来源合并、文献 API、论文分析）、`collection/`（采集各服务/源/工作流、期刊与源 API、期号删除、全文任务、能力声明与注册表）、`video_notes/`（视频模块）。测试临时目录统一在 OS 临时目录 `knowledge-vault-tests/` 下（规避 safe-delete 守卫，见 lessons L-004）。外部服务（Gemini、OpenAI Compatible、真实站点、浏览器）调用一律用 mock / fixture 离线覆盖（遵循 `AGENTS.md` 7.2）；确需真实调用时，把 `DATA_ROOT` 重定向到临时库副本再验证，不写正式运行数据（见 lessons L-011）。全量套件 197 个测试。

前端使用 Vitest 做纯逻辑测试（EndNote 解析、安全 Markdown、文献表单规范化、分析选择去重），当前 4 个文件共 8 项；Playwright 项目级 E2E 通过网络拦截覆盖 19 条路由、模型配置、论文分析、筛选、详情跳转、表单校验/创建、三种全文入口和移动端溢出，共 9 项。真实数据浏览器验收另行连接 Flask，避免自动化测试修改正式数据库或调用外部服务。
