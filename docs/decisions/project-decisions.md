# Project Decisions

按编号记录长期有效的重要设计决策。每条含编号、状态、日期、内容、理由与影响。

## D-001 采集能力整合进主项目

- 状态：已生效
- 日期：2026-03-04
- 内容：将采集能力整合进主项目，形成统一的前后端分离结构；采集中心采用数据库主存储 + 文件派生产物的模式；引入采集子域分层设计（models / repositories / services / providers / routes）。
- 理由：避免采集作为独立脚本体系游离在主项目之外，统一数据与代码边界。
- 影响：`backend/app/crawler/` 成为采集能力的唯一位置；原始数据先入库、派生产物可重建。

## D-002 仓库扁平化，根目录为唯一项目根

- 状态：已生效
- 日期：2026-04-02
- 内容：将原先嵌套在 `literature-manager/` 下的实际项目提升到仓库根目录；仓库根目录是唯一项目根，不再引入嵌套子应用根。
- 理由：消除嵌套根目录带来的路径复杂度和文档歧义。
- 影响：所有路径约定以仓库根为基准；运行时路径工具以同时存在 `backend/` 与 `frontend/` 的目录为工作区根。

## D-003 项目命名 Knowledge Vault

- 状态：已生效
- 日期：2026-04-02
- 内容：项目对外命名确定为 `Knowledge Vault`，建议 GitHub 仓库名 `knowledge-vault`。
- 理由：项目定位已从文献管理扩展为个人知识工作台，名称不再限定于文献场景。
- 影响：对外展示、文档与仓库命名统一使用该名称。

## D-004 视频转笔记作为独立域

- 状态：已生效
- 日期：2026-04-02
- 内容：新增独立的视频转笔记模块（`app/video_notes/`），拥有自己的任务模型、日志模型、路由和任务产物目录；后台任务式执行 `yt-dlp -> Whisper -> Gemini` 工作流；前端已接入。
- 理由：该模块与文献管理在概念上相互独立，不强行共用"文献/笔记"业务模型。
- 影响：独立域成为新增能力线的组织模板；其系统级工具依赖计划改为项目内依赖（见 D-006）。

## D-005 Gemini 代理配置走根目录 .env

- 状态：已生效
- 日期：2026-04-02
- 内容：Gemini 运行时从仓库根目录 `.env` 读取 `GEMINI_PROXY_URL`（也支持 `HTTPS_PROXY` / `HTTP_PROXY`），供翻译、期刊总结和视频笔记统一走本地代理；Key 读取优先级为环境变量 `GEMINI_API_KEY` → `backend/gemini_api_key.txt` → `gemini_api_key.txt`。
- 理由：本机无法直连 `generativelanguage.googleapis.com` 时需要代理；Key 与代理配置不进入版本库。
- 影响：`.env` 为本机私有配置，`.env.example` 为其可提交模板。

## D-006 环境策略：项目内依赖，不使用 conda

- 状态：已生效
- 日期：2026-08-30
- 内容：主项目 Python 环境为仓库根目录 `.venv`（依赖清单 `backend/requirements.txt`），前端依赖经 npm 安装；不使用 conda。视频转笔记模块当前仍依赖系统级工具（conda 环境 `whisper`、`yt-dlp`、FFmpeg），计划改为项目内部依赖，调整前需用户确认。
- 理由：环境独立、可复现，避免依赖系统公共 Python 和 conda 漂移。
- 影响：所有 Python 命令显式使用 `.venv\Scripts\python.exe`；新机器通过 requirements.txt 与 package-lock.json 重建环境。

## D-007 文档体系切换与 AGENTS.md 改写

- 状态：已生效
- 日期：2026-08-30
- 内容：`AGENTS.md` 全面改写（协作确认约定、环境约束、依赖管理、TDD、注释规范、文档自身维护规则）；文档体系切换为 `current-architecture` / `specifications/target-implementation-spec` / `decisions/project-decisions` / `lessons/engineering-lessons` 结构；原 `project-overview.md`、`development-guide.md`、`roadmap.md`、`project-log.md` 提炼迁移后删除。
- 理由：粗粒度介绍归 README、细粒度架构归 current-architecture；目标态、决策、经验分文档承载，避免单文档职责混杂；AGENTS.md 保持干净、客观、清晰。
- 影响：文档导航见 `docs/documentation-map.md`；本文档即新决策记录的起点（D-001~D-005 由旧 project-log 提炼）。

## D-008 版本控制策略：私有仓库，依赖与数据入库

- 状态：已生效
- 日期：2026-08-30
- 内容：仓库托管于 GitHub 私有仓库；`.venv/`、`frontend/node_modules/` 与全部运行数据（数据库、上传文件、任务产物）随仓库提交；`.crawler-browser-profile/` 与密钥类文件（`.env`、`gemini_api_key.txt`）不提交；SQLite 数据库按里程碑提交。
- 理由：跨机器直接可用，环境与数据不依赖本机状态；密钥安全是绝对底线；避免二进制快照膨胀。
- 影响：`.gitignore` 相应调整；采集的版权材料仅限私有仓库，转公开前需用户确认。

## D-009 采集与文献打通：统一论文实体 + 溯源

- 状态：已生效
- 日期：2026-08-31
- 内容：采集数据与文献工作台打通（T-4）：`literature` 成为统一论文实体，新增 `source`（imported/collection）、`source_raw_paper_id`（溯源到 raw_paper）、`journal_id`；raw_issue/raw_paper 保留为采集原始记录层（审计、重跑、合并依据）；采集入库走 `collection/pipeline/paper_merge.py` → `papers/services/paper_service.py` 的 upsert（依赖方向 collection → papers 单向，papers 不感知采集模型）。
- 理由：采集与导入殊途同归到单一实体；raw 层保留可重跑、可溯源；论文允许只有题录而无 PDF。
- 影响：合并规则为标题规范化去重（忽略大小写/空白），已存在只填空字段不覆盖用户数据；采集流程（ingestion_service）自动同步入库。

## D-010 期刊一等实体与采集源配置

- 状态：已生效
- 日期：2026-08-31
- 内容：新增 `journal` 表（name 唯一、issn、publisher）作为论文与采集共用的期刊实体（T-5 期刊筛选）；新增 `journal_source_config` 表记录每期刊支持的采集源（T-1，source_id 可选值 ncpssd/elsevier/cnki/official）；`/api/literatures` 支持 `journal_id` 过滤；新增 `/api/journals` 读写接口。
- 理由：期刊筛选与"按期刊选采集源"都需要期刊成为一等实体；期刊字符串字段（literature.journal）保留兼容前端列表。
- 影响：`journal_source_config` 是前端"选择采集源"的数据基础；cnki/official 仅注册标识，适配器实现待 T-1 任务。

## D-011 SQLAlchemy 约束命名约定

- 状态：已生效
- 日期：2026-08-31
- 内容：`db` 使用带 naming_convention 的 MetaData（ix/uq/ck/fk/pk 统一命名），约束自动获得稳定名称。
- 理由：SQLite 批量迁移要求约束必须有名字，否则 alembic 自动生成的迁移会因无名外键失败（"Constraint must have a name"）。
- 影响：后续 autogenerate 生成的约束均带标准名称；已应用的初始迁移不受影响。

## D-012 后端架构重构落地（六阶段）

- 状态：已生效
- 日期：2026-08-31
- 内容：后端重构按六阶段完成（PA 路径数据统一 / PB Flask-Migrate / PC 包结构重塑 / PD 采集文献打通 / PE 统一任务执行器 / PF 测试归位收尾），目标架构为 `core` 平台层 + `papers`/`collection`/`video_notes` 功能包，依赖单向 `collection → papers → core`；测试按包归位并统一在 OS 临时目录运行。
- 理由：渐进式迁移每阶段可独立验证提交，避免一次性大改动风险；行为与 API 全程保持不变。
- 影响：新增功能按"独立功能=新包、论文相关=papers 子模块、通用能力=core"落位；数据库结构统一走迁移管理。

## D-013 采集任务保持同步执行（异步化待前端配合）

- 状态：已生效（现状决策）
- 日期：2026-08-31
- 内容：PE 阶段核实采集任务（`POST /api/crawl-tasks`）为请求内同步执行（响应含 raw_issue）；保持现状，未接入异步执行器。
- 理由：异步化会改变 API 契约（响应先返回任务 id、结果需轮询），需前端配合改造，超出本次重构范围。
- 影响：`core/tasks.py` 执行器已就绪，未来采集变慢需异步化时可直接接入并同步改前端。

## D-014 桌面托盘启动器与端口统一编排

- 状态：已生效
- 日期：2026-09-02
- 内容：项目启动方式为根目录 `desktop.py`（经 `desktop.bat` 用 pythonw 无窗口拉起）：托盘图标常驻，后台管理前后端进程，右键退出按进程树回收；端口决策收口到启动器，经环境变量 `KV_BACKEND_PORT` / `KV_FRONTEND_PORT` 下发，策略为首选端口 + 自动顺延；`start.bat` / `stop.bat` 保留为无依赖备用入口。前后端仍走 HTTP 通信，未引入 Tauri / Electron / pywebview（用户不需要独立窗口）。
- 理由：用户痛点是三个常驻终端窗口与关闭不便，不是缺少桌面壳；零端口方案需重写整套通信层，成本远超收益；端口若三处各自写死，冲突时会出现「页面能开接口全挂」「启动成功打不开」等静默故障。
- 影响：`backend/app/core/ports.py` 为端口分配唯一实现（run.py 与启动器共用）；后端默认关闭 Flask 调试 reloader（与进程树管理冲突，热重载可用 `FLASK_DEBUG=1` 或托盘「重启服务」替代）；Vite 显式绑定 `127.0.0.1`，启动器注入端口时启用 `strictPort`；运行时端口与日志落 `.runtime/`（不提交）。

## D-015 采集源身份统一：source_type 存真实源 id，区域另立 region 列

- 状态：已生效
- 日期：2026-09-03
- 内容：`crawl_task` / `raw_issue` 的 `source_type` 值域由区域类别（domestic/foreign）改为真实采集源 id（ncpssd/magtech/elsevier），另加 `region` 列承担国内/国外语义；`journal_source_config.source_id` 同步收敛为注册表中的 source_id；语言推断改用 region。
- 理由：源身份与区域是两个正交维度，复用一个字段会让同一期刊在多源下采集时撞 `uq_raw_issue_identity` 唯一键（后采的覆盖先采的），语言推断也只能靠字符串硬匹配。
- 影响：新增采集源不再需要改动唯一键与语言推断；历史数据经迁移 `a3f7c1d92e05` 回填（domestic→ncpssd、foreign→elsevier）。

## D-016 采集源注册表 + 期刊级源配置由页面维护

- 状态：部分生效（内置期刊清单播种由 D-021 废止）
- 日期：2026-09-04
- 内容：新增 `app/collection/sources/registry.py` 作为 source_id → 实现的唯一映射，采集源通过类属性声明身份、区域、能力与所需配置字段；期刊的可用源、默认源与各源配置落在 `journal_source_config`，由 `/crawler/journals` 页面维护，「测试连接」结果落库复用；期刊区域（domestic/foreign）是期刊显式字段，由用户维护，决定该期刊可选的采集源范围（国内期刊用不了国外源，反之亦然）与论文语言语义。内置期刊清单由 `services/journal_seed.py` 播种（只补不覆盖）。
- 理由：此前「支持哪些期刊、每个期刊可选哪些源」散落在前端硬编码、legacy 缓存与路由常量三处，各自漂移，且前端无从得知源的能力差异（是否支持列期号、是否需要浏览器）。
- 影响：新增采集源只需实现接口并在注册表登记；采集台只能选择该期刊已启用的源，未配置源的期刊禁用提交并引导到配置页。

## D-017 官网源只取中文题录

- 状态：已生效
- 日期：2026-09-04
- 内容：Magtech 官网源只取中文题录：BibTeX 取作者/标题/卷期页码/关键词/DOI，EndNote（RIS）取摘要，每篇两个请求；英文标题与英文摘要不解析摘要页 HTML。
- 理由：两类结构化导出已覆盖题录需求，解析摘要页 HTML 成本高且易碎；当前分析场景不需要英文题录。
- 影响：官网源产出的 `title` / `abstract` 均为中文；需要英文题录时另行评估摘要页解析。

## D-018 前端迁移到 React + TypeScript + Vite

- 状态：已生效
- 日期：2026-09-05
- 内容：正式前端从 Vue 3 + JavaScript 迁移为 React 19 + TypeScript + Vite 8；使用 Tailwind CSS 4 与源码组件、TanStack Router、TanStack Query、React Hook Form + Zod、Axios、ECharts、Vitest / React Testing Library、Playwright、ESLint 和 Prettier。保持 Flask API、全部浏览器 URL、桌面托盘启动器、动态端口和主要用户行为不变；不采用 Next.js，迁移期不引入 TipTap。
- 理由：后续功能会持续扩展，需要更严格的类型合同、稳定的路由与服务端状态边界、可测试表单和长期可维护的组件源码；项目已有独立 Flask 后端，不需要 Next.js 的服务端能力。
- 影响：前端源码改为 `.ts` / `.tsx` 并按业务域懒加载；Vue、Pinia、Element Plus、Vue Router 与相关源码/依赖删除；Node.js 要求提升为 `^20.19.0` 或 `>=22.12.0`；活动 JavaScript chunk 继续受 500 KiB 检查约束。

## D-019 多来源文献溯源与字段级物化

- 状态：已生效
- 日期：2026-09-07
- 内容：同一 `literature` 可通过 `literature_source` 关联多个 `raw_paper`；论文匹配按 DOI 优先，否则按清洗标题 + 期刊 + 年份 + 期号。题录字段按 `用户编辑 > magtech > ncpssd > 其他来源` 分别物化并记录字段来源；人工编辑字段永久保护。删除或重采期号时按剩余关联重新计算，最后一个来源删除时保留统一文献及其知识整理数据。Magtech 标题只剥离严格配对、正确嵌套的 `bold` / `italic` / `sup` / `sub` 标签，异常标记保留原文并告警。
- 理由：同一期多源采集不能依赖“先到先占”，否则字段质量取决于采集顺序，删除来源后也无法可靠补位；字段级来源和人工保护使数据选择可解释、可回算。
- 影响：新增 `literature_source`、`user_edited_fields_json`、`field_sources_json` 和期号删除接口；旧 `source_raw_paper_id` 保留兼容但不再是完整溯源；文献详情显示关联来源与关键字段来源。

## D-020 全文 PDF 作为统一文献资产独立采集

- 状态：已生效
- 日期：2026-09-07
- 内容：全文 PDF 归属统一 `literature`，不归属 raw_issue；题录与全文是两个独立阶段，界面可一次发起但全文失败不回滚题录。支持文献单篇获取、Magtech 期号批量补采及题录后自动补采；任务异步执行并记录逐篇结果。批量跳过已有 PDF，用户上传 PDF 永不自动覆盖，单篇重新获取只替换当前 Magtech PDF；删除或重采来源期号保留 PDF 和来源快照，只清空失效 raw_paper 引用。当前不支持 NCPSSD、国外来源及需要绕过访问控制的全文获取。
- 理由：题录与大文件下载的失败模式、耗时和重试粒度不同；PDF 需要跨来源与期号生命周期长期保留，不能随原始采集记录删除；明确覆盖边界可避免自动任务破坏用户文件。
- 影响：新增 `source_ref_json`、PDF 来源/哈希/大小字段、`fulltext_task` / `fulltext_task_item`、三组全文 API 和前端入口；Magtech 下载结果校验 `%PDF-` 文件头与 100 MB 上限后原子落盘。

## D-021 移除内置期刊清单运行时入口

- 状态：已生效
- 日期：2026-09-07
- 内容：删除「导入内置清单」页面按钮、API、播种服务和测试；不删除数据库中已经存在的期刊与源配置。新数据库不预置业务期刊，由用户在「期刊与采集源」页面维护。
- 理由：该能力只用于把旧爬虫缓存迁入新期刊模型，不是长期产品功能；继续暴露会被误解为论文导入或采集，并把硬编码业务偏好带入正式系统。
- 影响：`journal` 可以为空；系统能力边界由采集源注册表声明，具体支持哪些期刊由用户配置决定。

## D-022 模型档案、场景绑定与密钥分离

- 状态：已生效
- 日期：2026-09-07
- 内容：`core/llm` 提供 Gemini Native 与 OpenAI Compatible 统一调用；模型档案记录协议、Base URL、模型名和连接状态，论文分析、论文翻译、视频笔记分别绑定默认档案。非敏感配置存 SQLite，API Key 只存根目录 `.env`，接口只返回是否已配置；旧 Gemini Key 来源保留兼容回退。
- 理由：模型供应商会持续变化，业务服务不应依赖某一 SDK；数据库随仓库提交，不能承载真实密钥。
- 影响：新增 `/settings/models`、`/api/llm`、`llm_profile`、`llm_scene_binding` 和 `openai` 依赖；后端 CORS 收窄到本机前端来源，防止任意网页修改模型地址后转发本机 Key。

## D-023 论文分析基于统一文献与输入快照

- 状态：已生效
- 日期：2026-09-07
- 内容：论文分析从采集期号详情中独立为 `/paper-analysis`；单期、多期和多篇选择最终都展开为去重后的 `literature_id` 集合，手工导入与采集论文共用流程。创建任务时保存题录输入快照，大输入在论文边界分批分析后再次综合，任务异步执行并保留历史结果。
- 理由：`raw_issue` 表示某一采集源快照，同一期多来源会造成论文重复；分析属于统一论文工作台，不应依赖论文的获取方式。快照保证论文后续编辑或删除不改变历史分析依据。
- 影响：新增 `paper_analysis` / `paper_analysis_item`、`/api/paper-analyses` 和独立导航入口；期号库只提供跳转快捷入口，旧详情页不再直接生成分析。
