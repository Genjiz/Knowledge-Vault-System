# Current Architecture

本文档记录已实现并经过验证的当前系统状态。目标态见 `docs/specifications/target-implementation-spec.md`。

## 技术栈

- 前端：React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + TanStack Router + TanStack Query + React Hook Form + Zod + Axios + ECharts
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + pywinauto + PyMuPDF4LLM + Docling + google-genai + openai
- 桌面启动器：pystray + Pillow（根目录 `desktop.py`，仅 Windows 使用）
- 开发环境：Windows x64；后端使用 Python `3.13.14` 与仓库根目录 `.venv`，前端使用 Node.js `24.17.0`、npm `11.13.0` 与 `frontend/node_modules`
- 环境重建：`.python-version`、`.node-version`、精确锁定的 `backend/requirements.txt` 和 `frontend/package-lock.json` 定义环境；根目录 `setup.ps1` 负责依赖安装、`.env` 初始化、数据库升级和基础验证；已安装依赖目录不进入 Git

## 后端结构

应用入口：`backend/run.py` → `app.create_app()`（app factory + 蓝图注册）。

按功能分包（2026-08-30 重构后）：

| 包 | 职责 | 内部结构 |
|---|---|---|
| `app/core/` | 平台层：跨包公共设施 | extensions（db/cors/migrate）、paths（数据目录唯一权威）、ports（端口分配唯一实现）、response、errors、health、tasks、llm/（模型档案、密钥存储、Gemini/OpenAI 适配器与 API） |
| `app/papers/` | 统一论文实体与文献工作台 | models（Literature/Tag/Folder/Note/Journal/JournalSourceConfig）、repositories、routes（/api/literatures /tags /folders /notes /backup）、services（统一文献业务） |
| `app/analysis/` | 论文分析独立业务域 | models（PaperAnalysis/PaperAnalysisItem/LiteratureTextAsset）、routes（/api/paper-analyses）、services（选择展开、Prompt 组装、全文解析缓存、分批分析） |
| `app/collection/` | 期刊采集管道 | models（CrawlTask/RawIssue/RawPaper/LiteratureSource/FullTextTask 等）、repositories、services（ingestion/translation/analysis/artifact/task/**source_runner**/**raw_issue**/**fulltext**）、routes（/api/crawl-tasks /raw-issues /fulltext-tasks /journals /collection）、sources（题录 SourceAdapter 注册表）、fulltext（Magtech/ScienceDirect 全文提供器解析与错误分类）、providers（兼容旧期号流程的 LLM 适配）、pipeline（paper_merge 多来源关联与字段物化）、runtime（普通 Edge 桌面自动化、受控 Chromium 与 legacy 路径）、legacy（历史脚本隔离区） |

依赖方向：`collection → papers → core`，`analysis → papers/core`。

蓝图前缀：`/api/literatures`、`/api/paper-analyses`、`/api/llm`、`/api/tags`、`/api/folders`、`/api/notes`、`/api/backup`、`/api/crawl-tasks`、`/api/raw-issues`、`/api/fulltext-tasks`、`/api/journals`、`/api/collection`、`/api/health`。

数据库结构由 Flask-Migrate（Alembic）管理，迁移脚本位于 `backend/migrations/`；`db.create_all()` 已从 app factory 移除（测试环境仍使用 create_all 建内存库）。当前迁移头为 `a8d4e6f1b203`；其最近迁移依次增加论文级卷期、拆分 Scopus 年度批次、增加分析全文资产与 Prompt 配置、增加 Prompt 模板快照、移除场景模型绑定并增加任务模型快照、增加全文任务人工处理状态，以及删除已剥离的视频任务表。

## 数据模型

- 统一论文实体：`literature`（题录 + `journal_id`；`user_edited_fields_json` 记录人工保护字段，`field_sources_json` 记录当前各字段来源；旧字段 `source` / `source_raw_paper_id` 保留兼容；`pdf_path` 可选，`pdf_source_type` / `pdf_source_raw_paper_id` / `pdf_sha256` / `pdf_size_bytes` 记录当前 PDF 来源与文件元数据）
- 期刊一等实体：`journal`（name 唯一、issn、publisher、region 区域为显式字段，决定可选源范围与论文语言语义）；`journal_source_config`（期刊-采集源配置，source_id 取自采集源注册表且区域须与期刊一致，含 enabled / is_default / config_json / 最近测试结果）
- 采集原始记录：`raw_issue`（以 source_type + journal + year + volume + issue 唯一标识；缺卷号为 `unknown`，缺期号为 `unassigned`；`expected_paper_count` 保存来源报告的应有篇数，API 实时返回题名、摘要和全文完成数）、`raw_paper`（保留为审计/重跑层，含 doi、论文级 volume / issue 与 `source_ref_json` 稳定源引用，入库时向 `literature` upsert 合并）
- 多来源关联：`literature_source`（一条 raw_paper 只关联一条 literature，一条 literature 可关联多个来源；删除 raw_paper 时级联删除关联）
- 采集核心表：`crawl_task`（source_type + region）、`crawl_task_log`、`raw_issue_analysis`、`llm_run`
- 模型平台：`llm_profile` 保存协议、Base URL、模型名、启用状态和测试结果。用户发起论文分析或论文翻译时必须提交具体模型档案；场景名称仅用于 Prompt 和调用类型分类，不绑定默认模型。API Key 不入库。
- 论文分析：`paper_analysis` 保存异步任务、模型、Prompt 模板版本与快照、自定义要求、全文使用/失败数和 Markdown 结果；`paper_analysis_item` 保存每篇统一文献的题录输入快照及所用全文资产引用。
- 全文文本资产：`literature_text_asset` 按 PDF SHA-256 + 解析管道版本唯一复用，记录实际解析器名称/版本、Markdown SHA-256、字符数、状态与失败尝试。
- 全文任务：`fulltext_task` 记录 single / issue / after_ingestion 任务总览；`fulltext_task_item` 记录逐篇来源、成功/失败/跳过/等待用户状态、稳定失败码、待处理公开 URL 及下载结果

合并规则（T-4）：DOI 非空时优先按 DOI 匹配，否则按清洗后的标题 + 期刊 + 年份 + 期号匹配。统一文献字段按 `用户编辑 > magtech > scopus > ncpssd > elsevier/其他来源` 逐字段选择首个非空值，因此一条文献可以混合多个来源字段；人工编辑字段不会被采集覆盖。论文级卷期优先于所属 raw_issue 的卷期。删除或重采采集批次后自动从剩余来源重新物化；最后一个来源删除时保留文献及其当前字段，并把非人工字段来源标记为 `retained`。`source_raw_paper_id` 指向当前最高优先级关联，仅用于旧代码兼容。

## 采集源与期刊配置（T-1）

采集源注册表 `app/collection/sources/registry.py` 是 source_id 与采集源实现的唯一映射：

| source_id | 显示名 | region | 采集粒度 | 列期号 | 需要浏览器 | 期刊级配置 |
|---|---|---|---|---|---|---|
| `ncpssd` | 国家哲社文献中心 | domestic | issue | 否 | 是 | 无（期刊 param 由 legacy 缓存解析） |
| `magtech` | 期刊官网（Magtech） | domestic | issue | 是 | 否 | `base_url`；支持全文 PDF |
| `elsevier` | Elsevier | foreign | issue | 否 | 是 | 无（slug 由 legacy 配置解析） |
| `scopus` | Scopus API | foreign | year | 否 | 否 | 无；从期刊实体读取 ISSN |

- 能力声明（`source_id` / `display_name` / `region` / `ingest_scope` / `capabilities` / `config_fields`）定义在 `sources/base.py` 的 SourceAdapter 上；新增采集源只需实现接口并在注册表登记，全链路生效。
- `source_type` 在 `crawl_task` / `raw_issue` 中存真实 source_id；`region` 承担国内/国外语义，供语言推断与前端分组。
- 源动作（测试连接、探测期号）收口在 `services/source_runner.py`，路由层只依赖其调用契约，测试可整体注入替换（`app.config["JOURNAL_SOURCE_RUNNER"]`）。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/collection/sources` | 源注册表与能力清单 |
| GET / PUT | `/api/collection/elsevier-key` | 查询 Elsevier Key 是否已配置，或保存/清除密钥；不返回明文 |
| GET | `/api/journals` | 期刊 + 已配置源 + 采集统计 |
| POST / PUT / DELETE | `/api/journals[/\<id\>]` | 期刊增删改 |
| PUT | `/api/journals/<id>/sources` | 批量提交该期刊全部源配置（未提交的源删除，至多一个默认源） |
| POST | `/api/journals/<id>/sources/<source_id>/test` | 测试源连通性，结果落库供列表展示 |
| GET | `/api/journals/<id>/issues?source_id=&year=` | 探测某年可用期号 |
| DELETE | `/api/raw-issues/<id>` | 删除指定来源的采集期号、原始论文和派生产物；保留统一文献并按剩余来源回算 |
| POST | `/api/raw-issues/<id>/refresh` | 按年份重新查询 Scopus，并只覆盖目标卷期；空结果保留原数据 |
| POST | `/api/literatures/<id>/fulltext-tasks` | 按文献来源解析 Magtech 或 ScienceDirect 全文；`replace_existing=true` 只替换同一自动来源 PDF |
| POST | `/api/raw-issues/<id>/fulltext-tasks` | 为 Magtech 或可解析 PII 的 Scopus 卷期批量补采缺失全文 |
| POST | `/api/fulltext-tasks/<id>/resume` | 在完成人工验证或恢复浏览器、桌面、网络环境后继续 `waiting_user` 任务 |
| GET | `/api/fulltext-tasks[/<id>]` | 查询全文任务总览和逐篇结果，可按文献或期号过滤 |

系统不再内置或自动导入期刊清单；新数据库的期刊为空，由「期刊与采集源」页面维护。期刊区域是用户维护的显式字段，采集源按区域与期刊匹配，配置接口会拒绝区域不符的源。

Scopus 源按 `ISSN(<journal.issn>) AND PUBYEAR = <year>` 使用 COMPLETE 视图分页采集，每页 25 条并按 `coverDate` 排序；一次年度任务按论文的真实 volume + issue 拆成多个 raw_issue，同一期号跨卷保持独立。定向重采仍查询整年再精确过滤目标卷期，过滤为空时不覆盖旧批次。客户端使用 `requests.Session(trust_env=False)`，不读取代理环境变量或 Windows 自动代理；429/5xx 有限重试，401/403 提示校内出口 IP 权益。EID、PII、DOI 用于源引用与去重，DOI 参与统一文献匹配。正式 IP&M 2026 数据已拆为 11 个卷期批次，并保持 601 个 raw_paper ID 与 601 条来源关联。

## 模型平台与论文分析

- `/settings/models` 管理多个 Gemini Native / OpenAI Compatible 模型档案；连接测试只返回状态，API Key 永不回传。
- 非敏感模型配置存 SQLite；页面保存的 Key 以 JSON 映射写入根目录 `.env` 的 `LLM_API_KEYS_JSON`。已迁移的 Gemini 档案在未配置专属 Key 时兼容读取 `GEMINI_API_KEY` 或历史 Key 文件。
- Gemini `base_url` 可空（使用官方地址），OpenAI Compatible 必须显式提供 API 根地址；业务服务统一调用 `LLMService.generate_text`。
- 后端 CORS 只允许 `127.0.0.1` / `localhost` 的 HTTP 端口来源，防止外部网页修改 Base URL 后借后端发送本机密钥。
- `/paper-analysis` 的“整期分析”和“自选论文”互斥；整期按期刊 → 年份 → 卷号 → 期号展开并自动纳入该期全部统一文献，不要求逐篇再次勾选。
- “自选论文”通过文献库综合关键词查询访问全部统一文献，按 30 篇分页并跨页保留勾选；查询覆盖标题、作者、期刊、摘要和关键词。
- 默认 Prompt 通过 API 和页面展示；用户自定义要求追加到默认 Prompt。创建任务时保存模板版本、模板快照和自定义要求快照。
- 可选全文分析会读取统一文献 PDF：PyMuPDF4LLM 优先、Docling 回退，解析结果缓存为 Markdown；分析项只引用文本资产，模型调用时读取实际 Markdown 内容。解析失败会持久化逐篇警告并继续用题录分析。
- 分析任务由 `TaskExecutor` 异步运行；超长单篇全文也会按字符预算确定性分块，多批结果再次综合并落库，同时写入 `backend/data/artifacts/paper-analysis/<task_id>/analysis.md`。

Magtech 官网源走纯 HTTP 结构化导出（同类站点可复用 `base_url` 配置接入）：年页 `showTenYearVolumnDetail.do?nian={year}` → 期页 `volumn_{id}.shtml` → 文章 id → `getTxtFile.do?fileType=BibTeX`（题录/关键词/DOI）与 `fileType=EndNote`（摘要），每篇 2 个请求，无需浏览器。论文外部页按文章 id 固定生成 `/CN/abstract/abstract{id}.shtml`，不采用 BibTeX 中可能落入软 404 的 `/CN/abstract/article_{id}.shtml`；迁移同时规范化已有原始论文和统一文献 URL。标题中的 `bold` / `italic` / `sup` / `sub` 仅在标签严格成对且正确嵌套时清除；未配对、错误嵌套或未知标签保留原文并记录 warning。全文使用稳定 article_id 请求 `downloadArticleFile.do?attachType=PDF&id=<article_id>`；响应需以 `%PDF-` 开头且不超过 100 MB，验证后通过同目录临时文件原子替换。已实测情报学报官网 PDF 接口返回有效 `%PDF-1.4` 文件。

全文采集与题录合并相互独立：采集台可勾选题录完成后补采 Magtech 全文，文献详情与期号详情还可按已有来源补采；PDF 失败不回滚题录。全文提供器与题录源分离：Magtech 原始记录按 article_id 下载，Scopus 原始记录存在 PII 时解析为 ScienceDirect。Scopus 返回的紧凑 PII 和 `S0306-4573(25)00349-8` 形式的带符号 PII 均可识别；原始采集值保持不变，进入 ScienceDirect 提供器前严格规范化为 17 位紧凑 PII。批量任务跳过已有 PDF；用户上传 PDF 永不被自动覆盖；单篇重新获取只替换同一自动来源 PDF。同一期号删除或重采时保留已下载 PDF，只把失效的 raw_paper 引用置空。

ScienceDirect 提供器使用 PII 构造公开文章页，并通过 `runtime/edge_desktop.py` 控制用户日常 Edge `Default` profile：等待可见 `View PDF`，用系统级鼠标输入点击，确认新标签页为目标 PII 的 `pdf.sciencedirectassets.com` 签名 PDF，再通过 `Ctrl+S` 和系统“另存为”控件把唯一临时文件保存到上传目录。临时文件必须同时通过 `%PDF-` 文件头、末尾 `%%EOF`、稳定大小和 100 MB 上限校验，读取后立即删除，再由全文服务原子写入正式 PDF。签名 URL、Cookie、IP、challenge 正文和 reference number 均不入库，只保存稳定文章 URL。

ScienceDirect 下载严格串行并由进程级锁保护；成功后只关闭当前 PDF 与文章标签页。桌面必须处于解锁的交互式 Windows 会话，Edge 必须可见且未最小化，执行期间会短暂占用前台焦点和鼠标。明确的人机 challenge 会保留当前文章页并把任务暂停为 `waiting_user`，用户手动处理后通过恢复接口继续；程序不求解验证码。普通 Edge 缺失、启动失败或后端无法连接交互式桌面时归类为可恢复的 `browser_unavailable`，同样暂停任务而不是记为终态失败。连续 `Internal Server Error` 或网络出口拒绝归类为 `access_blocked`，订阅不足归类为 `access_denied`。

全文 API 仍通过 `TaskExecutor` daemon 线程执行；普通 Edge 网关在每个任务线程内显式初始化并释放 COM apartment，避免 pywinauto 首次导入线程与后续任务线程不一致导致 UIA 失效。

校园网下已用普通 Edge 对 IP&M PII `S0306457326004826` 完成网关和临时数据库任务两层 smoke test：任务状态与条目状态均为 `completed`，PDF 为 21 页，文件哈希与 `literature`、任务条目记录一致，正式数据库未被测试写入。专用 DrissionPage profile 把 Cookie 和动态链接转入 `requests` 的旧路径仍会返回 `403 / CPE00001`，不再用于 ScienceDirect 全文下载。

IP&M 2026 年第 `2PA` 期（raw_issue 12）的 12 个带符号 PII 已完成真实批量验证：首轮成功 11 篇，1 篇因 Edge 临时保存结果不是 PDF 而安全失败；再次创建期号任务时自动跳过 11 篇已有 PDF并补齐缺失论文。最终 12 个 PDF 共 247 页、45,778,403 字节，全部可解析且文件哈希与任务记录一致。

「测试连接」是轻量探测，不采集论文、不落临时文件：`magtech` 请求年页解析期号并回报识别结果；`ncpssd` 校验期刊定位参数是否已缓存 + 站点探活；`elsevier` 校验期刊 slug 是否已配置 + 站点探活；`scopus` 使用 STANDARD 视图请求一条记录并校验 Key、ISSN 与连通性。仅测试结果状态会写入 `journal_source_config`。

## 前端结构与页面

入口为 `frontend/src/main.tsx`，应用壳与路由位于 `src/app/`。`AppShell` 提供 Workspace / Analysis / Collection / System / Utilities 五组导航；TanStack Router 按业务域懒加载页面；TanStack Query 管理服务端数据与后台任务轮询。

- `src/api/`：Axios client、统一响应信封与错误模型、TypeScript API 合同；数组查询参数按重复 key 序列化。
- `src/components/`：基于原生元素与 Radix primitives 的源码组件，以及按需注册模块的 ECharts 封装。
- `src/features/`：按 dashboard、literatures、analysis、settings、organize、utilities、collection 划分页面与业务逻辑。
- 文献表单使用 React Hook Form + Zod；论文分析 Markdown 经过本地安全解析后渲染；普通笔记仍使用文本输入，不引入富文本编辑器。
- Tailwind CSS 4 由 Vite 插件接入，组件视觉规则保留在 `src/index.css`；生产构建按业务域拆包，`scripts/check-chunk-sizes.mjs` 强制活动 JavaScript chunk 不超过 500 KiB。

| 路由组 | 页面 |
|---|---|
| `/`、`/statistics` | 仪表盘、统计分析 |
| `/literatures`、`/literatures/new`、`/literatures/<id>`、`/literatures/<id>/edit` | 文献列表、创建、详情与编辑 |
| `/paper-analysis` | 单期、多期或多篇论文分析、任务历史与结果 |
| `/tags`、`/folders` | 标签与文件夹管理 |
| `/import`、`/backup` | 导入、备份与恢复 |
| `/crawler/journals`、`/crawler/tasks`、`/crawler/settings` | 期刊与采集源配置、采集任务台、采集服务密钥 |
| `/crawler/issues`、`/crawler/issues/<id>` | 原始期号库与详情、翻译及论文分析跳转 |
| `/settings/models` | 模型档案、模型密钥与连接测试 |

期刊与采集源页面不发起采集；采集任务台只使用该期刊已启用的源。issue 粒度源显示期号输入，year 粒度源只显示年份。采集期号库按期刊 → 年份 → 卷号 → 期号展示，`unknown` / `unassigned` 分别显示为“卷号未知”/“未分期”；统一文献层不保存这些内部标记。Scopus 详情可重采目标卷期，也可对存在 PII 的论文补采 ScienceDirect 全文。全文任务暂停时，期号详情与文献详情显示失败原因、公开文章页和继续操作；只有 `verification_required` 使用“验证完成后继续”，其他可恢复状态统一使用“继续下载”。外文期号翻译要求选择具体模型，翻译后可用“原文 / 中文译文”分段控件切换显示。采集服务密钥在独立采集设置页维护。

## 数据与产物

运行数据统一位于 `backend/data/`（路径由 `app/core/paths.py` 唯一定义，可用环境变量 `DATA_ROOT` 整体重定向）：

- 主数据库：`backend/data/db/app.db`（SQLite）
- 上传文件：`backend/data/uploads/pdfs/`
- 采集产物：`backend/data/artifacts/crawler/raw-json/<source>/<journal>/<year>/<volume>/<issue>.json`（`ARTIFACT_ROOT`）
- 全文 Markdown 资产：`backend/data/artifacts/literature-text/<pdf_sha256>/<pipeline_version>/content.md`
- 论文分析产物：`backend/data/artifacts/paper-analysis/<task_id>/analysis.md`

原则：数据库是主存储；JSON/Markdown 是派生产物，用于重跑、审计、导出与复核。

## 运行时路径规则

- 运行数据目录统一由 `app/core/paths.py` 定义（`DATA_ROOT` 环境变量可整体重定向）；各目录保留独立环境变量覆盖（`DATABASE_URL`、`ARTIFACT_ROOT`、`UPLOAD_FOLDER`）。
- 运行时路径工具从代码位置向上查找同时包含 `backend/` 和 `frontend/` 的目录作为工作区根（`app/collection/runtime/paths.py`）
- 受控 Chromium profile 目录：`.crawler-browser-profile/`（可用环境变量 `CRAWLER_BROWSER_DATA_ROOT` 覆盖）；ScienceDirect 全文不使用该目录，直接复用普通 Edge `Default` profile
- 采集历史脚本位于 `backend/app/collection/legacy/`，由 source 适配器动态加载包装
- 浏览器可执行文件探测覆盖 Chrome、Chromium 和 Microsoft Edge 常见 x64/x86 路径，可用环境变量 `CRAWLER_BROWSER_PATH` 覆盖
- 模型 API Key 映射位于根目录 `.env` 的 `LLM_API_KEYS_JSON`（不提交）；数据库只存非敏感模型配置。
- Elsevier Research Products API Key 位于根目录 `.env` 的 `ELSEVIER_API_KEY`（不提交）；设置页和接口只显示是否已配置。

## 代理与网络路由

- 根目录 `.env` 使用标准 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`，不再使用模型专用代理变量。Gemini 按 `HTTPS_PROXY` → `HTTP_PROXY` 读取后显式传给 SDK；OpenAI Compatible 使用 HTTPX 默认环境代理行为。
- Scopus、NCPSSD 与 Magtech 使用 `requests.Session(trust_env=False)`，不读取应用层代理环境或 Windows 自动代理。NCPSSD 的入口预检及四个 legacy 网络组件共享同一个直连 Session；已验证其摘要接口无 Cookie 仍返回完整数据，源码不再保存静态 Cookie。
- Elsevier/ScienceDirect 浏览器流量由 Edge/Chromium、Windows 系统代理、浏览器扩展及 TUN/aTrust 决定；Python 代理变量不会直接配置浏览器。
- `desktop.py` 不加载 `.env`；它复制父进程环境并增加端口变量。后端运行时加载 `.env`，且已有同名进程环境变量优先。桌面健康检查显式使用空 `ProxyHandler`，保证回环探测不经过应用层代理。
- TUN、VPN 和 aTrust 属系统路由层；`trust_env=False` 不能绕过它们。完整矩阵与排查方法见 `docs/proxy-and-network.md`。

## 启动方式与端口管理

- 推荐入口：根目录 `desktop.bat` → 无窗口拉起 `desktop.py`（pythonw）。启动器负责：单实例检测（`.runtime/ports.json` + 健康检查）、端口分配、后台拉起前后端（`CREATE_NO_WINDOW`，日志落 `.runtime/logs/`）、轮询 `/api/health` 就绪后用系统默认浏览器打开界面、托盘常驻（打开界面/重启服务/退出），退出按进程树 `taskkill /f /t` 回收。
- 端口规则：决策收口在启动器，经环境变量下发——`KV_BACKEND_PORT` → `backend/run.py`，`KV_BACKEND_PORT`/`KV_FRONTEND_PORT` → `frontend/vite.config.ts`。策略为首选端口（5000/3000）+ 自动顺延；显式注入的端口被占时报错，未注入时自动顺延。`app/core/ports.py` 是端口分配的唯一实现。
- 后端默认关闭 Flask 调试 reloader（`FLASK_DEBUG=1` 可开启）；Vite 显式绑定 `127.0.0.1`，启动器注入端口时启用 `strictPort`。
- 端口记录与进程日志位于 `.runtime/`（不提交），退出后删除端口记录文件。

## 当前限制

- 文献工作台的 tag/folder/note/backup 业务逻辑仍在路由层（未下沉 service）
- 期刊筛选后端能力已就位（`/api/literatures?journal_id=`），前端筛选 UI 未接
- 采集任务为同步执行（请求内跑完）；如需异步化需改 API 契约并配合前端轮询（core/tasks 执行器已可用）
- 全文自动采集目前支持已配置的国内 Magtech 期刊官网，以及可由 Scopus PII 定位且当前机构会话有权访问的 ScienceDirect 论文；NCPSSD、其他出版社和无订阅权限的页面不支持，也不绕过访问控制
- ScienceDirect 普通 Edge 自动化仅支持 Windows 交互式桌面；锁屏、最小化 Edge 或下载期间操作鼠标与切换焦点可能中断当前论文
- 全文任务由进程内 daemon 线程执行，应用重启不会自动恢复未完成任务
- 论文分析任务同样由进程内 daemon 线程执行，应用重启不会自动恢复未完成任务，可从历史记录重新分析
- Magtech 年页 `showTenYearVolumnDetail.do` 仅覆盖近十年，更早年份的期号探测未实现
- 官网源只取中文题录，英文标题/摘要需解析摘要页 HTML，未实现

## 后台任务执行器

`app/core/tasks.py` 提供统一 `TaskExecutor`（PE 阶段落地）：daemon 线程包装 + `submit(task_id, fn, on_error)` + `is_running/running_ids` 状态查询；异常经 `on_error(exc)` 回调由调用方落库。已接入全文下载和论文分析任务（均包装 app context，失败回调落库）。题录采集任务仍保持请求内同步执行，题录后的全文下载是独立异步阶段。

## 测试组织

`backend/tests/` 按包归位：`core/`、`papers/`、`analysis/`、`collection/`。外部服务调用使用 mock / fixture 离线覆盖；当前全量套件 257 个测试。

前端使用 Vitest 做纯逻辑测试，当前 6 个文件共 19 项；Playwright 项目级 E2E 覆盖路由、已移除功能的旧入口、论文分析互斥选择与 Prompt 配置、Scopus 年度采集/卷期重采、全文入口、显式模型选择和移动端溢出，共 14 项。
