# 采集源扩展与期刊支持能力建设

日期：2026-09-02
状态：已完成

## 1. 目标与范围

### 1.1 目标

1. 新增「期刊官网」采集源，以《情报学报》（Magtech 架构）为首个落地案例，采集题录数据（标题、作者、摘要、关键词、DOI、卷期页码等）。
2. 采集任务可按期刊选择采集源，同一期刊在不同源之间可切换。
3. 建立「当前支持哪些期刊、每个期刊可用哪些源」的可视化能力，替代目前散落各处的硬编码清单。
4. 为 T-2（全文 PDF 采集）预留接入点，本期不实现。

### 1.2 不在本期范围

- 全文 PDF 下载（T-2），仅预留接口与能力标记。
- 单篇论文采集（T-3，仍待定）。
- NcpssdSource / ElsevierSource 内部实现重写（保留原实现，仅补齐能力声明）。
- 采集异步化（D-013 已记录，另立任务）。

## 2. 现状调研结论（已验证事实）

### 2.1 三个真问题

| 问题 | 现状 | 影响 |
|---|---|---|
| 采集源身份语义冲突 | `crawl_task.source_type` / `raw_issue.source_type` 存的是区域类别 `domestic` / `foreign`；`journal_source_config.source_id` 存的是真实源 id（`ncpssd`/`elsevier`/`cnki`/`official`） | 新增 official 源后，《情报学报》2026 年第 3 期在 ncpssd 与 official 两个源下会撞 `uq_raw_issue_identity` 唯一键，后采的覆盖先采的；`paper_merge` 目前还用 `source_type == "domestic"` 推断语言 |
| 支持期刊清单分散 | NCPSSD 源 → `backend/app/collection/legacy/domestic/journal_url_cache.json`（4 个：情报学报、现代情报、图书情报知识、情报理论与实践）；Elsevier 源 → 代码内 `journal_slugs`（IP&M）；前端 → `CrawlTaskCenter.vue` 硬编码 `defaultJournals`；数据库 `journal` 表 → 0 行 | 用户无法从系统内得知支持范围，四处清单各自漂移 |
| 采集源无注册表 | 仅 `routes/journal.py` 内硬编码 `SUPPORTED_SOURCE_IDS = {"ncpssd","elsevier","cnki","official"}` | 新增源要改多处；前端无法知道源的能力差异（是否需要浏览器、是否支持列期号、是否支持 PDF） |

### 2.2 情报学报官网接口探测结果（2026-09-02 实测）

官网 `https://qbxb.istic.ac.cn` 确认为 Magtech（玛格泰克）系统（Apache-Coyote、JSESSIONID、`/CN/volumn/home.shtml` 模板）。

| 步骤 | 接口 | 实测产出 |
|---|---|---|
| 年 → 期列表 | `GET {base}/CN/article/showTenYearVolumnDetail.do?nian={year}` | 该年全部期：`volumn_1242.shtml` ↔ `2026 Vol.45 No.6 pp.777-924 2026-07-15` |
| 期 → 文章 id 列表 | `GET {base}/CN/volumn/volumn_{id}.shtml` | `../abstract/abstract1034.shtml` … `abstract1043.shtml`（2026 年第 6 期 10 篇） |
| 题录 | `GET {base}/CN/article/getTxtFile.do?fileType=BibTeX&id={N}` | author / title / journal / year / volume / number / pages / keywords / doi / url |
| 摘要 | `GET {base}/CN/article/getTxtFile.do?fileType=EndNote&id={N}` | RIS：`%X` 中文摘要、`%8` 出版日期 |
| PDF（T-2 预留） | `GET {base}/CN/article/downloadArticleFile.do?attachType=PDF&id={N}` | 未实测，接口存在 |

**关键结论：官网源不需要浏览器自动化**，纯 HTTP GET + 结构化导出接口即可，稳定性优于现有 NCPSSD 源（依赖 DrissionPage）。同类 Magtech 站点（图书情报工作、情报理论与实践、情报科学、情报杂志等）复用同一套接口，一个 `MagtechSource` 按 `base_url` 配置可服务多个期刊。

已知待验证边界：

- `showTenYearVolumnDetail.do` 仅覆盖近十年，更早年份需回退 `showOldVolumn.do` / `showTenYearOldVolumn.do` 页解析。
- 英文题录（英文标题/摘要）在 BibTeX/EndNote 中不含，需额外解析 `/CN/abstract/abstract{N}.shtml` HTML 页。
- 反爬与请求频率限制未做压测，需加请求间隔与重试。

## 3. 已确认决策与约束

- 遵循 `AGENTS.md`：改动前先确认，复杂任务按本计划执行；TDD；改结构后同步更新 `docs/current-architecture.md`。
- 后端环境 `.venv`，前端 `frontend/npm run build` 收尾验证。
- 项目已有 `SourceAdapter`（`app/collection/sources/base.py`），现有两源尚未实现；`journal`、`journal_source_config` 表已存在但无数据。
- 依赖方向不得反转：`collection → papers → core`。
- 采集内容本期只做题录，不做全文。

### 3.1 用户已确认决策（2026-09-02）

| 决策点 | 结论 |
|---|---|
| 采集源身份统一 | 方案 A：`crawl_task.source_type` / `raw_issue.source_type` 值域改为真实 source_id（`ncpssd` / `magtech` / `elsevier`），另加 `region` 列承担 `domestic` / `foreign` 语义，供语言推断与前端分组 |
| 官网源题录范围 | 只取中文题录：BibTeX 取作者/标题/卷期页码/关键词/DOI，EndNote 取摘要，每篇 2 个请求，不解析摘要页 HTML |
| 本期接入期刊 | 只接《情报学报》一个 Magtech 站，跑通后再横向扩展 |
| 期刊数据初始化 | 从 `journal_url_cache.json` 导入 NCPSSD 的 4 个期刊，预置情报学报 Magtech `base_url`，之后由「期刊与采集源」页面增删改 |

## 4. 实施步骤

### 阶段 0：修订 SourceAdapter 接口（对齐现实）

把 `base.SourceAdapter` 的方法签名对齐现有实现的真实形态，避免为接入新源重写老源逻辑：

```python
class SourceAdapter:
    source_id = ""        # ncpssd / magtech / elsevier
    display_name = ""
    region = ""           # domestic / foreign，供语言推断与前端分组
    capabilities = {}     # {"list_issues": bool, "download_pdf": bool, "needs_browser": bool}

    def fetch_issue(self, journal_name, year, issue, **kwargs): ...  # 必选，与现有实现一致
    def list_issues(self, journal_name, year, **kwargs): ...         # 可选能力
    def download_pdf(self, paper_ref, **kwargs): ...                 # 可选能力（T-2）
```

`NcpssdSource` / `ElsevierSource` 只需补充类属性即完成能力声明，内部逻辑不动。

### 阶段 1：MagtechSource 实现（TDD，离线测试）

新增 `backend/app/collection/sources/magtech.py`：

- `list_issues(journal_name, year)` → 解析年页，返回 `[{volume, issue, pages, published_at, source_url, volumn_id}]`
- `fetch_issue(journal_name, year, issue)` → 定位期页 → 抽取文章 id → 并发受限地拉取 BibTeX + EndNote → 组装为与 `NcpssdSource.fetch_issue` 完全一致的返回结构
- 字段映射：`title`/`authors`/`abstract`/`abstract_zh`（中文源两者相同）/`keywords_json`/`pages`/`doi`/`detail_url`/`published_at`/`sort_index`
- 新增 `doi` 与 `volume` 字段到 `raw_paper` / `raw_issue`（`volume` 已有，`doi` 需新增）
- 请求控制：可配置间隔（默认 0.5s）、超时、重试
- 测试：以本次抓取的真实响应作为 fixture 放入 `backend/tests/fixtures/`，纯离线解析测试；网络调用用 mock 覆盖重试/超时/空结果

### 阶段 2：SourceRegistry + 采集源身份统一

新增 `backend/app/collection/sources/registry.py`：

- `SOURCES = {"ncpssd": ..., "magtech": ..., "elsevier": ...}` 注册表
- `get_source(source_id, config)` → 按 `journal_source_config.config_json`（如 Magtech 的 `base_url`）构造实例
- `describe_sources()` → 返回给前端的源元信息与能力清单
- 移除 `routes/journal.py` 中硬编码的 `SUPPORTED_SOURCE_IDS`，改由注册表校验

采集源身份统一（**方案待用户确认，见第 8 节**）：

- 方案 A（推荐）：`crawl_task.source_type` / `raw_issue.source_type` 值域改为真实 source_id，另加 `region` 列承担区域语义
- 方案 B：保留 `source_type` 为区域，新增 `source_id` 列

配套：迁移脚本（新列 + 回填现有 1 条 `domestic` → `ncpssd`）、`raw_issue` 唯一键调整、`paper_merge` 语言推断改用 `region` 或期刊语言。

同批次 `journal_source_config` 新增字段（支撑阶段 4 的测试与默认源）：

- `is_default`（Boolean）——该期刊的默认采集源，每个期刊至多一个
- `last_checked_at`（DateTime）、`last_check_status`（String：ok / warn / failed）、`last_check_message`（Text）——最近一次测试的结果，供列表页直接展示

### 阶段 3：期刊与源配置 API + 数据播种

- `GET /api/collection/sources` → 源注册表：source_id、显示名、能力、`config_schema`（声明每个源需要哪些配置项）
- `GET /api/journals?with_sources=1` → 期刊 + 已启用源 + 统计（已采集期数、最近采集时间、上次测试状态）
- `POST /api/journals` / `PUT /api/journals/<id>` → 新增与编辑期刊
- `PUT /api/journals/<id>/sources` → 批量提交该期刊全部源配置（启用状态、默认源、各源 config）
- `POST /api/journals/<id>/sources/<source_id>/test` → 测试单个源配置，返回识别结果与状态并落库
- `GET /api/journals/<id>/issues?source_id=&year=` → 探测某年可用期号（Magtech 原生支持；不支持的源返回 `capabilities` 标记）
- `DELETE /api/journals/<id>` → 删除期刊（已有采集数据时需二次确认）
- 播种数据：预置情报学报等期刊、可用源与 Magtech `base_url`；NCPSSD 的期刊清单从 `journal_url_cache.json` 导入，后续由 UI 维护

### 阶段 4：前端布局

#### 4.1 页面职责切分（2026-09-02 修订）

期刊的**添加、配置、测试**收敛到独立页面，采集台只负责**发起采集**，两页靠链接互相跳转。

| 页面 | 路由 | 职责 | 不做什么 |
|---|---|---|---|
| 期刊与采集源 | `/crawler/journals`（新增） | 新增/编辑期刊、配置该期刊可用源、测试源连通性、查看采集统计 | 不发起采集 |
| 采集任务台 | `/crawler/tasks`（改造） | 选期刊 → 选源 → 选年 → 探测期号 → 发起采集 → 查看任务记录 | 不新增/修改期刊，不配置源 |

导航位置：插入 `App.vue` 的 Collection 分组**首位**（配置先行），位于「采集任务台」之前。

#### 4.2 期刊与采集源页（JournalSources.vue）

**主体：卡片网格**（期刊量级为数十，卡片比表格更适合展示源标签，且与现有页面卡片风格一致）

每张卡片：期刊名 / 区域 | ISSN · 出版方 | 可用源标签组（默认源高亮） | 已采集期数 · 最近采集时间 | 操作（配置源、编辑、删除）

顶部：页头 + 统计卡（支持期刊数 / 已配置源组合数 / 已采集期数）+「新增期刊」按钮
空态：无期刊时引导新增，并提供「从 NCPSSD 缓存导入」入口

**配置用右侧抽屉 `el-drawer`**（非弹窗——配置项含多源开关 + 每源配置 + 测试结果，需要更大横向空间与可滚动区域）

抽屉内容自上而下：

1. 基本信息：期刊名、ISSN、出版方、区域（国内/国外）
2. 采集源配置：注册表返回的**每个源一行**
   - 启用开关（`el-switch`）
   - 该源所需配置项（Magtech 填 `base_url`，按注册表声明的 `config_schema` 动态渲染；无需配置的源不显示输入框）
   - 「测试」按钮（未启用或未填必填项时禁用）
   - 测试结果就地显示：成功 → 绿色提示 + 识别到的期刊名与最新期号；失败 → 红色提示 + 具体原因
   - 默认源单选（`el-radio`），只能从已启用源中选
3. 底部固定操作栏：取消 / 保存

必填校验：启用某源但该源要求的配置项为空时，保存拦截并定位到该行。

#### 4.3 测试连接的行为定义（关键）

测试不只是探活，而是**取回可识别信息让用户确认没配错站点**：

| 源 | 测试动作 | 成功返回 |
|---|---|---|
| `magtech` | 请求 `{base}/CN/article/showTenYearVolumnDetail.do?nian={当年}` 并解析 | 站点识别到的期刊名 + 最新期号（如「情报学报 · 2026 年第 7 期」），与当前期刊名不符时给出黄色告警 |
| `ncpssd` | 校验 `journal_url_cache.json` 中是否存在该期刊 param + 站点可达预检 | 「已收录，param 已缓存」或「未收录，需先补充 param」 |
| `elsevier` | 校验 `journal_slug` 是否配置 + 站点可达预检 | 「slug 已配置」或「缺少 slug」 |

测试为**同步请求**（单次 HTTP，量级小），超时 8 秒。结果落库到 `journal_source_config` 新增字段：`last_checked_at`、`last_check_status`（ok / failed / warn）、`last_check_message`，卡片上显示「上次测试：通过 / 失败」，避免每次进页面都要重测。

#### 4.4 采集台改造（CrawlTaskCenter.vue）

- 删除硬编码 `defaultJournals`，改为从 `/api/journals?with_sources=1` 拉取
- 联动：选期刊 → 源下拉只显示该期刊**已启用**的源，默认选中默认源
- 年份 + 源 → 「探测期号」按钮，列出该年可用期号供点选（源不支持时提示手填）
- 任务卡片显示源显示名而非 `domestic` / `foreign`
- **两页衔接**：期刊无已启用源时，禁用「发起采集」并提示「该期刊未配置可用采集源」，附跳转按钮到 `/crawler/journals`

### 阶段 5：文档与验证

- 更新 `docs/current-architecture.md`（新增源、注册表、source_id 语义、API）
- 更新 `docs/specifications/target-implementation-spec.md`（T-1 落地、新增 Magtech 源）
- 更新 `docs/decisions/project-decisions.md`（新的长期决策，编号递增）
- 运行全量后端测试 + `npm run build`

## 5. 当前进度

- [x] 现状调研与官网接口实测
- [x] 阶段 0：SourceAdapter 接口修订（能力声明 + config_fields）
- [x] 阶段 1：MagtechSource 实现（离线 fixture 解析测试 + 重试/超时 mock）
- [x] 阶段 2：SourceRegistry + 采集源身份统一（迁移 a3f7c1d92e05 已应用并回填历史数据）
- [x] 阶段 3：期刊与源配置 API + 数据播种
- [x] 阶段 4：前端布局（`/crawler/journals` 新页面 + 采集台改造 + 导航入口）
- [x] 阶段 5：文档与验证

## 6. 计划偏差

1. **期刊区域不新增列**：计划 4.2 拟在抽屉中编辑期刊「区域」，实现改为由该期刊已启用采集源的区域推导（domestic / foreign / 国内外）。理由：区域是源的属性，单独立列会与源配置产生两份互相漂移的数据。
2. **新增期刊与配置源合并为一个抽屉**：计划 4.2 的「新增/编辑期刊」与「配置源」操作在 UI 上合并为统一的「配置」入口（抽屉内含基本信息与源配置两段），减少重复入口。
3. **播种入口改为 API + 页面按钮**：`journal_seed` 以 `POST /api/journals/import-known` 暴露，页面空态与顶部均提供「导入内置清单」，未单独提供 CLI 脚本（遵循不新增 standalone 脚本入口的约定）。
4. **老源补充「测试连接」**：`NcpssdSource` / `ElsevierSource` 按 4.3 的表格补充了 test_connection（校验 param/slug 是否就绪 + 站点可达预检），原计划只在阶段 1 覆盖 Magtech。

## 7. 验证结果

- 后端全量测试 150 项通过（阶段 1~3 均按 Red → Green 推进：源能力声明、注册表、期刊与源 API、播种、老源测试连接）。
- 迁移 `a3f7c1d92e05` 已应用；迁移前数据库备份到 `tmp/app.db.bak-sourceid`。
- 情报学报官网源真实连通性实测：`test_connection` 返回 ok（识别到 2026 年共 7 期，最新第 7 期），`list_issues(2026)` 返回 7 条期号数据。
- 开发库播种结果：4 个期刊入库，情报学报配置 ncpssd + magtech（magtech 为默认源，base_url 已预置）。
- 接口冒烟：`GET /api/collection/sources`、`GET /api/journals`（含源与统计）、期号探测、测试连接均返回预期。
- 前端 `npm run build` 通过，`JournalSources` 已产出独立分包。
- 端到端采集实测（数据目录由 `DATA_ROOT` 重定向到 `tmp/e2e-magtech`，未触碰正式运行数据）：以 `magtech` 源采集情报学报 2026 年第 7 期，任务 completed，raw_issue 落 10 篇（volume 45）；标题/作者/摘要/关键词/DOI/页码零缺失；10 篇全部经 paper_merge 合并进 `literature`（`source=collection` + `source_raw_paper_id` 溯源）。

## 8. 遗留问题

已提炼到 `docs/current-architecture.md` 的「当前限制」，本计划不再留存：

- 全文 PDF 采集（T-2）：`MagtechSource.download_pdf` 仅返回直链，下载与落盘未接
- Magtech 年页仅覆盖近十年，更早年份的期号探测未实现
- 官网源仅取中文题录，英文标题/摘要需解析摘要页 HTML

## 9. 决策点

全部已于 2026-09-02 经用户确认，结论见第 3.1 节。执行过程中形成的长期决策已录入 `docs/decisions/project-decisions.md`（D-015 ~ D-017）。
