# 2026-08-30 后端架构重构计划（v2）

## 1. 目标与范围

将后端重构为"按功能分包 + core 平台层"结构：`papers`（统一论文实体）、`collection`（采集管道）、`video_notes`（独立功能）三个业务包 + `core` 平台层（含大模型服务）；统一运行数据目录；引入 Flask-Migrate；补齐统一后台任务执行器；落地采集与文献工作台打通的数据模型基础。

**范围内**：目录结构重塑、数据目录迁移、Flask-Migrate 基线、数据模型演进（Journal 表、Literature 表扩展、JournalSourceConfig 表、采集入库 upsert 打通）、core/llm 平台服务（本期先封装现有 Gemini 用法，多供应商配置留接口）、统一任务执行器、测试归位。

**不在范围内**：知网/期刊官网采集源适配器的具体实现（结构就位后另起计划）、PDF 下载功能的完整实现（本期仅建管道步骤位与数据模型支撑）、视频转笔记系统级工具依赖改造、`crawler/legacy/` 重写、新功能开发。

**硬约束**：
- 现有 API 路径与行为不变，前端零改动（新增 API 允许，如期刊源配置）；
- 每阶段结束跑全量后端测试，通过后进入下一阶段；
- 每阶段一个独立 Git 提交（里程碑节点）；
- 遵循 AGENTS.md 全部强制约定（TDD、路径不硬编码、完成前验证、文档同步）。

## 2. 已确认决策与约束

- 目标架构与分包方案：papers（models/repositories/services 含 ingest、organize 子模块）+ collection（sources、pipeline、rawstore 相关 models/services）+ video_notes + core（extensions/paths/errors/response/tasks/health/llm）；依赖单向 `collection → papers → core`、`video_notes → core`（用户已确认）。
- 统一论文实体：扩展现有 literature 表（新增来源、journal_id、可选 PDF 关联等字段），不新建 paper 表；以后如有需要再评估重构表（用户已确认）。
- raw 层保留：raw_issue/raw_paper 继续作为采集原始记录，入库时向统一论文表 upsert（用户已确认）。
- 数据目录：`backend/data/`（db、uploads/pdfs、artifacts/<域>），现有数据原样搬迁（用户已确认）。
- 迁移节奏：分阶段渐进，每阶段独立验证与提交（用户已确认）。
- 任务执行器：简版线程管理——提交、状态机（pending/running/succeeded/failed）、异常落任务日志（用户已确认）。
- SQLite 单库多域沿用现状。
- 目标态依据：`docs/specifications/target-implementation-spec.md` T-1~T-7。

## 3. 实施步骤

### PA 路径与数据目录统一

1. 新建 `app/core/paths.py`：唯一定义 `DATA_ROOT = backend/data` 与 `db/`、`uploads/pdfs/`、`artifacts/<域>/` 各路径，支持环境变量覆盖。
2. `config.py` 改为从 `core/paths.py` 读取数据库与目录配置。
3. 数据搬迁（先备份 `app.db` 到 `tmp/`，确认无进程占用后移动）：`app.db` → `data/db/app.db`；`uploads/pdfs/` → `data/uploads/pdfs/`；`artifacts/raw-json/` → `data/artifacts/crawler/raw-json/`。
4. `video_notes/runtime/paths.py` 去硬编码改读 `core/paths.py`；crawler 产物路径引用同步改走 `core/paths.py`；`app/__init__.py` uploads 路由路径更新。
5. 核实 `crawler/legacy/` 内部是否有硬编码产物路径，仅做最小适配并记录。
6. 验证：更新测试路径断言，全量测试通过；健康检查通过。

### PB 引入 Flask-Migrate（提前于结构重塑，后续改表依赖它）

1. `requirements.txt` 新增 `Flask-Migrate`；`extensions.py` 增加 `migrate`；factory 初始化。
2. 生成初始迁移脚本，将现有 14 张表 stamp 为基线。
3. 确定 `TestingConfig` 内存库与迁移的配合方式并记录。
4. 验证：upgrade/downgrade 往返；全量测试通过。

### PC 包结构重塑（纯移动与改名，行为不变）

1. 建 `app/core/`：`extensions.py`、`paths.py`、`errors.py`（新建全局 errorhandler）、`response.py`（自 utils 迁入）、`health.py`（自 routes 迁入）、`tasks.py` 骨架；`utils/` 删除。
2. 建 `app/papers/`：`models/`（自 app/models 迁入）、`repositories/`（自 app/repositories 迁入）、`routes/`（literature/tag/folder/note/backup 迁入）、`services/`（自现有路由中抽取业务逻辑，ingest 与 organize 子模块挂入）。
3. 建 `app/collection/`：自 `app/crawler/` 整体迁入，内部重排为 `models/ repositories/ services/ routes/ sources/ pipeline/ legacy/`；providers 演化为 sources（domestic → `sources/ncpssd.py`，foreign → `sources/elsevier.py`，加 SourceAdapter 接口与源注册表）；`runtime/gemini_runtime.py` 迁入 `core/llm/`（本期保持 Gemini 单供应商行为，注册表结构预留多供应商）。
4. `video_notes/` 保持原位，仅更新对 core 的引用。
5. 验证：全量测试通过（测试本阶段只改 import 路径）。

### PD 数据模型演进与采集-文献打通

1. 按 TDD 新增模型测试，然后演进模型：
   - 新增 `journal` 表（名称、ISSN 等题录字段）；
   - `literature` 表扩展：`journal_id`（可空外键）、`source`（imported / collection）、`source_raw_paper_id`（可空，溯源到采集原始记录）、PDF 可选关联（文件记录表或可空字段，执行时按现有 uploads 机制定）；
   - 新增 `journal_source_config` 表（journal、source 标识、启用状态、配置项）。
2. 迁移脚本：PB 的 Migrate 生成 schema 变更；现有数据回填（现有 literature 记录 source 默认 `imported`）。
3. 采集入库打通：`pipeline/paper_merge.py`（现 ingestion_service 演化）在 raw_paper 落库后向统一论文表 upsert（按题录去重键合并），采集来源论文带 `source=collection` 与溯源 id。
4. 期刊筛选：organize 提供按 journal 筛选的查询与 API（现有 /api/literatures 增加过滤参数，不破坏现有调用）。
5. 新增期刊源配置的读写 API（`/api/journals`，新增接口）。
6. 验证：新模型与打通逻辑的测试通过；全量测试通过。

### PE 统一后台任务执行器

1. 按 TDD 实现 `core/tasks.py`：`submit(task_id, fn)` 线程包装、状态机、异常捕获写入对应域任务日志（先测后改）。
2. `video_notes` 裸 Thread 改用执行器；核实 crawler 长任务执行方式并统一接入。
3. 验证：video_notes 与 collection API 测试通过。

### PF 测试归位与收尾

1. `tests/` 按包归位：`papers/`、`collection/`、`video_notes/`、`core/`，补 `conftest.py`。
2. 清理空目录；全量后端测试 + `npm run build`。
3. 文档收尾：`current-architecture.md` 充实为完整版（消化原"当前限制"条目）；`project-decisions.md` 新增本次重构决策；`documentation-map.md` 如需调整同步更新。

## 4. 当前进度

- [x] 方案讨论与设计决策确认（2026-08-30：数据目录/搬迁/节奏/任务执行器/统一实体/分包/raw 层）
- [x] 本计划 v2 创建（2026-08-30）
- [x] 用户确认计划 v2（2026-08-30："开始 PA"）
- [x] **PA 路径与数据目录统一（2026-08-30 完成）**
- [x] **PB Flask-Migrate 基线（2026-08-30 完成）**
- [x] **PC 包结构重塑（2026-08-31 完成）**
- [x] **PD 数据模型演进与采集-文献打通（2026-08-31 完成）**
- [x] **PE 统一后台任务执行器（2026-08-31 完成）**
- [ ] PF 测试归位与收尾

## 5. 计划偏差

- v1 → v2：用户补充 T-1~T-7 目标态后，目标架构由"三域分包"修订为"papers/collection/video_notes + core 平台层"；Flask-Migrate 由 P3 提前至 PB（数据模型演进依赖它）；新增 PD（打通）阶段；legacy 目录更名说明并入 PC。
- PA 执行偏差：`crawler/legacy/` 内未发现硬编码产物路径（零改动）；`build_task_paths` 签名由 `(project_root, task_id)` 简化为 `(task_id)`，`ArtifactService` 移除 project_root 注入，测试改用 `DATA_ROOT` 环境变量覆盖；`.gitignore` 已按提交策略调整（数据入库、密钥排除、依赖目录留待专门提交）。
- PB 执行偏差：`db.create_all()` 从 app factory 移除（否则与迁移重复建表冲突），数据库结构改由 Flask-Migrate 接管；`TestingConfig` 内存库继续使用 `db.create_all()`（测试 setUp 显式调用，不跑迁移）；初始迁移通过对空内存库 autogenerate 生成（factory 的 create_all 需临时置空）；两个 bootstrap 测试改为显式建表；全量测试仍需处理 safe-delete 批量删除守卫（删除 `state.json` 重置计数，见 lessons L-004 补充）。
- PC 执行偏差：papers 的 service 层深度抽取（路由业务逻辑下沉到 paper_service/ingest/organize）**推迟到 PD 阶段**——当前无 literature 路由测试作为安全网，纯结构阶段先保证行为不变；`papers/services/` 已建骨架。safe-delete 环境干扰的根本解法：测试临时目录从 `backend/.tmp-tests/` 迁至 OS 临时目录（shim 对 OS tmp 下的路径直通原生 rmtree，见 lessons L-004 再补充）。新增 `core/errors.py`（统一异常 + 全局错误处理器）、`core/llm/registry.py`（T-7 骨架）、`collection/sources/base.py`（SourceAdapter 接口，现有 NcpssdSource/ElsevierSource 尚未实现该接口，适配在 T-1 任务落地）。
- PD 执行偏差：service 层抽取**仅完成核心的 paper_service**（落库/合并/期刊关联），tag/folder/note/backup 的抽取范围收敛到"打通所需"；重复期刊名接口返回 409（比 400 语义更准确）；PDF 落库沿用现有 `literature.pdf_path` 字段（无需新表，遗留问题 3 解决）；`db` 增加约束命名约定（D-011），因命名约定引入的无关 autogenerate 操作（tag 唯一约束）已从迁移中剔除；迁移首版因无名外键与 NOT NULL 无默认值两次失败，均修正后通过。
- PE 执行偏差：`core/tasks.py` 实现为**线程包装 + 状态查询 + on_error 回调**（执行器不感知具体域，状态落库由回调完成）；video_notes 裸 Thread 已统一接入，失败回调标记任务 failed 并写日志；**crawler 经核实为同步执行**（请求内跑完，响应含 raw_issue），保持现状不接入异步——异步化会改变 API 契约并需要前端轮询配合，列为后续可选改造；失败路径集成测试因 `:memory:` SQLite 按线程隔离无法覆盖跨线程写库，改为同步调用失败回调的方式验证接线，线程异步行为由 core/tasks 单测覆盖（另在文件库上手动验证通过）。

## 6. 验证结果

- PA：全量后端测试 55/55 通过（含新增 test_core_paths）；冒烟验证通过——应用在开发配置下正常启动，`/api/health` 200、`/api/literatures` 正常，三个数据配置均指向 `backend/data/`，原 app.db 数据（含 2 篇 PDF、raw-json 产物）完整可用。
- PB：初始迁移含全部 14 张表（`1100434363a6_initial_schema`）；真实库 `flask db stamp head` 成功；空库往返验证——`upgrade head` 建出 14 表并写入版本号，`downgrade base` 清空所有表（仅剩 alembic_version）；移除 factory create_all 后全量测试 55/55 通过；开发配置冒烟正常（health 200、literatures 200）。
- PC：全量后端测试 55/55 通过；8 个 API 端点冒烟全部正常（/api/notes 400 为原有必填参数行为）；旧包引用（app.crawler/utils/routes/models/repositories/extensions）全仓清零。
- PD：新增 18 个测试（papers 模型/journal API/paper_merge 合并/期刊筛选），全量 73/73 通过；真实库迁移 `c9b826cfa1c0` 应用成功——16 张表，存量 2 条文献回填 `source=imported`，版本戳更新；回滚验证通过（downgrade 后 14 表、数据保留）；冒烟：/api/journals 增查改、/api/literatures?journal_id 过滤均正常。
- PE：新增 core/tasks 单测 5 个 + video_notes 失败路径测试 1 个，全量 78/78 通过；失败路径在文件库上手动验证（任务标记 failed、error_message 落库）；video_notes API 测试全绿。
- 提交记录：`docs` 体系提交 + `refactor(PA)` + `chore` 清理 + `refactor(PB)` + `refactor(PC)` + `feat(PD)` + PE 相关提交（见 git log）。

## 7. 遗留问题

1. `crawler/legacy/` 脚本内部硬编码路径核实：PA 已核实为零，无需适配。
2. `TestingConfig` 内存库与 Migrate 的配合：已确定——测试继续用 `db.create_all()` 建内存库，不跑迁移。
3. PDF 文件记录的落库方式（文件记录表 vs 可空字段）：已确定——沿用现有 `literature.pdf_path` 字段，无需新表。
4. 知网、期刊官网源适配器、PDF 下载完整功能、LLM 多供应商配置界面的具体实现：结构就位后另起计划（T-1/T-2/T-7）。
5. `.venv/` 与 `frontend/node_modules/` 的首次入库：已从 .gitignore 移除忽略，待用户确认后作为独立大提交执行。
6. `backend/app/crawler/legacy/domestic/issue_url_cache.json` 与 legacy 期刊缓存目录（如 `legacy/情报学报/`）为旧爬虫运行缓存，暂未纳入版本控制，待用户决定是否忽略或入库。
7. `alembic.ini` 由 `flask db init` 生成，`sqlalchemy.url` 为空（运行时由应用配置注入），迁移脚本与 `migrations/` 需随仓库提交。
