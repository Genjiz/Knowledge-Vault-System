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
