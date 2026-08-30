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
