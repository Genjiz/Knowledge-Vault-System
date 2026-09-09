# IP&M / Scopus 按年题录采集

日期：2026-09-09
状态：已确认，可实施

交接说明：按本文件实现。入库形状、source_id、密钥位置或采集粒度若要改，先改本文件。密钥、ISSN、代理与测试约束按下列各节执行。

## 1. 目标与范围

### 1.1 目标

把《Information Processing & Management》的国外题录采集从 ScienceDirect 浏览器抓取换成 Scopus Search API，按「期刊 + 年」一次入库。

完成后应能：

1. 采集台选择该期刊、选择年份、发起采集；不填写期号，不探测期号。
2. 写入标题、摘要、作者、关键词、DOI、PII、EID、卷号、期号、页码、出版日期、文章 URL。
3. 合并进统一文献，DOI 参与去重。
4. Elsevier Research Products API Key 在系统设置中配置和更换；不进期刊配置、不进数据库、接口不回传明文。

### 1.2 本期做

- 只做 Elsevier / IP&M 这条国外题录链路。
- 新增采集源 `scopus`。
- 题录入库；DOI / PII / EID / URL 必须落到 `raw_paper`。
- 现有 `elsevier` 浏览器源保留并仍可配置，不当默认，不删除。

### 1.3 本期不做

- 任何全文 PDF 自动下载，包括 Unpaywall、机构登录浏览器 View PDF、ScienceDirect Article Retrieval / PDF。
- Springer、WoS、CNKI。
- 采集台按期、按月、探测期号。
- 把 `GEMINI_PROXY_URL` 重命名为 `PROXY_URL`。
- Nature Energy 爬虫里的 Gemini 筛选。
- 采集任务异步化。
- 自动把参考爬虫 `.env` 里的 key 写入本项目。
- 预置 IP&M 期刊行（D-021：期刊由用户在「期刊与采集源」页维护）。

## 2. 已确认决策与约束

| 项 | 结论 |
|---|---|
| 采集粒度 | 采集台只选期刊 + 年。查询不使用 `VOLUME()` / `ISSUE()`，也不用官方 `date`。 |
| 主源 | `source_id=scopus`，展示名「Scopus API」，`region=foreign`。 |
| 查询 | `ISSN({journal.issn}) AND PUBYEAR = {year}` |
| 视图 | 采集用 `view=COMPLETE`。401/403 时任务失败并提示校园网 / aTrust，不自动降级 STANDARD。 |
| 分页 | `sort=coverDate`，`count=25`，`start` 从 0 步进，直到取完或 `start` 触及约 5000 上限。 |
| HTTP | `requests.Session(trust_env=False)`，不传 `proxies`。不走 Clash / `HTTP_PROXY` / `HTTPS_PROXY` / `PROXY_URL` / `GEMINI_PROXY_URL`。 |
| 出口 IP | Scopus COMPLETE 权益跟出口 IP。校内直连或 aTrust。 |
| 密钥 | 系统级 `ELSEVIER_API_KEY`，同一时间一把。配额按 key、按 API、按周。 |
| ISSN | 只用 `journal.issn`。IP&M 填印刷 ISSN `0306-4573`。缺 ISSN 不能启用 scopus，测试连接失败。 |
| 入库 | 一年一条 `raw_issue`，`issue` 哨兵值 `year`。卷期写在每篇 `raw_paper` 上。 |
| 浏览器源 | `elsevier` 仍注册。用户可在期刊配置里关闭。 |
| 全文 | `download_pdf=false`。不改 D-020。 |
| 代码 | TDD；新代码注释用中文；测试和日志不含真实 key。 |

### 2.1 Scopus Search 入参（本期用到的子集）

文档：https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl 、 https://dev.elsevier.com/guides/ScopusSearchViews.htm

| 参数 | 官方语义 | 本期 |
|---|---|---|
| `query` | 布尔检索，必填 | `ISSN(0306-4573) AND PUBYEAR = 2025` |
| `view` | STANDARD / COMPLETE | 采集 COMPLETE；测试连接 STANDARD `count=1` |
| `date` | 粒度是年，例 `2002-2007` | 不用 |
| `start` / `count` | 偏移与页大小；COMPLETE 每页最多 25 | 0, 25, 50, ... |
| `sort` | 最多 3 个字段 | `coverDate` |
| `field` / `content` / `subj` / `cursor` | 可选 | 不用 |

返回记录带 `prism:volume`、`prism:issueIdentifier`，只写入论文字段，不当采集过滤条件。STANDARD 无摘要。

本机直连（参考爬虫里的 Research Products Key，`trust_env=False`）曾测得：Search STANDARD/COMPLETE 200；Abstract Retrieval 200；Serial Title 200；ScienceDirect Search/Metadata 200 但不能按 ISSN+年列目录；Article Retrieval/PDF 403。经 Clash 时 COMPLETE 出现过 401/超时。

### 2.2 现有实现必须改的点

- 国外源只有 `elsevier`：浏览器抓期页，一年一卷，不写 `raw_paper.doi`。
- `POST /api/crawl-tasks` 对所有源要求 `issue`。
- `paper_merge` 把 `raw_issue.volume/issue` 写到统一文献；一年多卷或期号为 `2PA` 时不能靠「第 N 期」身份。
- 前端 `SourceMeta.capabilities` 是布尔表。采集粒度不能塞进这个表。
- `get_source()` 只透传 `config_fields`。ISSN 在 `journal.issn`，Key 在 `.env`，都不会自动进源构造函数。
- 期刊启用源时只校验 `config_fields` 必填项；scopus 没有 config_fields，必须另做 ISSN 校验。

## 3. 方案

### 3.1 源合同

`describe_source` 与 `GET /api/collection/sources` 增加并列字段 `ingest_scope`，取值 `issue` 或 `year`。缺省 `issue`。不要放进 `capabilities`。

- `source_id = scopus`
- `display_name = Scopus API`
- `region = foreign`
- `metadata_priority = 250`（高于 elsevier 的 100；与国内源无交叉）
- `capabilities.list_issues = false`
- `capabilities.download_pdf = false`
- `capabilities.needs_browser = false`
- `ingest_scope = year`
- `config_fields = []`

`ncpssd` / `magtech` / `elsevier` 不声明时视为 `issue`。`describe_source` 对所有源都返回显式 `ingest_scope`。

继续使用 `fetch_issue(journal_name, year, issue, **kwargs)`，不新增 `fetch_year`。scopus 忽略传入的 `issue`，返回的 `issue.issue` 恒为字符串 `year`。

### 3.2 ISSN、期刊名与密钥怎么进源

ISSN 不进 `journal_source_config.config_json`。

1. `IngestionService.run_ingestion` 按 `journal_name` 读 `Journal.issn`，调用 `provider.fetch_issue(..., issn=issn)`。
2. `SourceRunner.test_connection` 增加 `issn=`，由期刊测试连接接口传入 `journal.issn`。
3. `ScopusSource` 自身再读 `ELSEVIER_API_KEY`。缺 key 或 ISSN 为空则失败。
4. 启用 scopus 时，若 `journal.issn` 为空则 400，提示需要先填写期刊 ISSN。

期刊名只用于展示和 `raw_issue.journal_name`。检索只用 ISSN。现有「IP&M」或全名都可以。不播种期刊。用户在期刊页填写 ISSN `0306-4573`，启用 scopus 并设为默认。

### 3.3 字段映射

Scopus COMPLETE entry 写入本系统：

- `eid`（否则 `dc:identifier`）→ `source_identifier`，并写入 `source_ref_json.eid`
- `pii` → `source_ref_json.pii`
- `prism:doi` → `doi` 与 `source_ref_json.doi`
- `dc:title` → `title`
- COMPLETE `author` 列表（`authname` 或 given+surname）逗号拼接；没有则 `dc:creator` → `authors`
- `dc:description` → `abstract`
- `authkeywords` 按 ` | ` 拆分 → `keywords_json`
- `prism:pageRange`，否则 startingPage-endingPage → `pages`
- `prism:coverDate` → `published_at`
- `prism:volume` → `raw_paper.volume`
- `prism:issueIdentifier` → `raw_paper.issue`（原样保留，允许 `2PA`）
- 有 PII 则 `https://www.sciencedirect.com/science/article/pii/{PII}`，否则有 DOI 则 `https://doi.org/{doi}` → `detail_url`

`source_ref_json` 只放 eid / pii / doi。

丢弃规则：无标题，或 eid/doi/pii 都空，记入任务日志并计入 dropped，不入库。同年结果按 eid → doi → pii 去重。不按 document type 过滤。

`sort_index` 按 API 返回顺序从 0 递增。`paper_count_hint` 用 `opensearch:totalResults`。实际入库数与 total 不一致时任务可以 completed，日志写 warning。`start` 到上限仍有剩余则任务失败并说明截断。

`raw_issue.volume` 置空。`language=en`。

### 3.4 HTTP 客户端

新文件 `backend/app/collection/sources/scopus.py`。客户端可同文件，过长再拆。不新增 `httpx`。算法可对照 `参考代码/nature energy 爬虫/src/scopus_collector/search_api.py`，不要 import 那个包，不要读它的 `.env`。

- URL：`https://api.elsevier.com/content/search/scopus`
- Header：`X-ELS-APIKey`、`Accept: application/json`
- timeout 60s；页间隔 0.5s；429/5xx 有限次退避
- 每次创建 Session 都 `trust_env=False`
- 默认测试套件不打真网

密钥每次从环境变量和根目录 `.env`（`dotenv_values`）读取。不要只在进程启动时 `load_dotenv(override=False)`。设置页写入后用 `set_key` 并同步 `os.environ`。

### 3.5 入库与合并

一年一条 raw_issue，身份为 `(scopus, journal_name, year, year)`。`crawl_task.issue` 同样为 `year`。现有产物路径会生成 `raw-json/scopus/<journal>/2025/year.json`，可直接用。

Alembic 迁移，down_revision `f6a1c2d3e4b5`：给 `raw_paper` 增加可空 `volume`、`issue`，`String(50)`。历史行不回填。

`raw_paper_repo.replace_for_issue` 写入 volume / issue / doi / source_ref_json。

`paper_merge._paper_data`：文献 volume/issue 优先 `raw_paper`，为空再回退 `raw_issue`。`_SOURCE_REGION["scopus"] = "foreign"`。

翻译、分析仍按一条 raw_issue 处理全年，不改任务模型。重采同一年走现有按身份覆盖。

### 3.6 API

`POST /api/crawl-tasks`：

- `ingest_scope=issue`：必填 `source_type, journal_name, year, issue`
- `ingest_scope=year`：必填 `source_type, journal_name, year`；忽略客户端 issue；入库 issue 为 `year`
- scopus 若 `download_fulltext=true` 继续 400

`GET /api/journals/:id/issues`：scopus 仍返回不支持列期号。前端不调用。

采集密钥放在 collection 域，不要写入 `LLM_API_KEYS_JSON`：

- `GET /api/collection/elsevier-key` 返回 `{ "has_api_key": bool }`
- `PUT /api/collection/elsevier-key` body 为 `{ "api_key": "..." }` 或 `{ "clear": true }`
- 写入根目录 `.env` 的 `ELSEVIER_API_KEY`；响应不含明文
- `.env.example` 增加空值 `ELSEVIER_API_KEY=`

测试连接：有 key + ISSN 后请求 STANDARD `count=1`。不采论文。

### 3.7 前端

判断 year-scope 用 `sourceMeta.ingest_scope === "year"`，不要写死 `source_id === "scopus"`。

改动文件：

- `frontend/src/api/types.ts`：`SourceMeta` 增加 `ingest_scope`；`capabilities` 保持布尔开关
- `frontend/src/api/resources.ts`：year-scope 创建任务不传 issue；密钥 GET/PUT
- `frontend/src/features/collection/pages.tsx`：采集台、期刊源标签、任务列表、期号库、期号详情
- `frontend/src/features/analysis/pages.tsx`：选项文案
- `frontend/src/features/literatures/pages.tsx`：来源展示名增加 scopus
- `frontend/src/features/settings/pages.tsx`：同一页增加「采集密钥」卡片，不新建路由
- `frontend/e2e/app.spec.ts`：mock 补 `ingest_scope`

文案：`issue === "year"` 显示「YYYY 年」，不要「第 year 期」。抽取小函数，采集台、期号库、详情、分析、删除确认共用。

采集台 year-scope：只留期刊、源、年、发起采集。隐藏期号输入、探测按钮、全文勾选。提交不依赖 issue。

期刊源行：year-scope 显示「按年采集」。启用 scopus 时 ISSN 为空，前端也拦一层，以后端为准。

### 3.8 全文

本期只存标识。`download_pdf` 为 false。用户上传 PDF 的现有入口保持。国外自动下载另开计划。

## 4. 主要改动文件

新增：

- `backend/app/collection/sources/scopus.py`
- `backend/app/collection/routes/elsevier_key.py`（或并入 `sources.py`）
- `backend/tests/collection/test_scopus_source.py`
- `backend/tests/collection/test_elsevier_key_api.py`
- `backend/tests/fixtures/scopus/` 脱敏 COMPLETE JSON
- Alembic 迁移

修改：

- `backend/app/collection/sources/base.py`、`registry.py`、`__init__.py`
- `backend/app/collection/services/source_runner.py`、`ingestion_service.py`
- `backend/app/collection/routes/task.py`、`journal.py`
- `backend/app/collection/models/raw_paper.py`
- `backend/app/collection/repositories/raw_paper_repo.py`
- `backend/app/collection/pipeline/paper_merge.py`
- `backend/app/papers/routes/__init__.py`
- `.env.example`
- 第 3.7 节所列前端文件
- 实现完成后的架构 / 决策 / 目标态文档

## 5. 实施步骤

每阶段先写失败测试再写实现。

### 阶段 0：合同

`describe_source` 返回 `ingest_scope`。更新 `test_source_capabilities.py`、`test_source_registry.py`、`test_journal_sources_api.py`：源集合从三源变为四源，并断言 scopus 的 ingest_scope=year。

### 阶段 1：客户端离线测试

fixture 覆盖：单页、多页、空结果、401、403、429、缺摘要、缺 DOI、`issueIdentifier=2PA`、PII 转 URL、无身份丢弃、去重。断言 query、`trust_env=False`、不读进程代理。

### 阶段 2：ScopusSource + 注册表

`test_connection`：无 key / 无 ISSN / 网络失败 / 200。`fetch_issue` 组出 3.1 与 3.3 的 payload。

### 阶段 3：密钥 API 与设置页

用临时 `.env` 测读写与清除。响应无明文。同步 `.env.example`。

### 阶段 4：入库

迁移 volume/issue。year-scope 的 crawl-tasks。paper_merge 论文级卷期。ISSN 启用校验。回归 Magtech / NCPSSD / elsevier 按期合同。

### 阶段 5：前端

采集台、期号文案、设置卡片、e2e mock。最后 `npm run build`。

### 阶段 6：文档

- `docs/current-architecture.md`：新源、year-scope、密钥、Scopus 直连、限制。只写已跑通的事实。
- `docs/decisions/project-decisions.md`：新增 D-024。草案：国外 Elsevier 期刊题录主源为 Scopus Search API；采集台按期刊+年；一年一条 raw_issue，论文自带卷期；系统级 ELSEVIER_API_KEY；Scopus HTTP 直连不走代理；本期不下载国外全文。
- `docs/specifications/target-implementation-spec.md`：T-1 国外主源改为 Scopus API；T-2 国外全文仍未开通。
- 本计划填写进度与验证。

## 6. 测试清单

- `test_source_capabilities.py` / `test_source_registry.py`：四源 + ingest_scope
- `test_scopus_source.py`：解析、分页、错误、连接测试、payload
- `test_crawler_api.py`：year-scope 不要求 issue；带 issue 的旧请求仍有效；scopus 拒绝 download_fulltext
- `test_journal_sources_api.py`：启用 scopus 无 ISSN 失败；test_connection 传入 issn
- ingestion 测试：假源按年入库，doi/volume/issue 落到文献
- `test_elsevier_key_api.py`：has_api_key、写入、清除
- 现有 Magtech 全文与按期采集回归

运行：仓库根目录 `.venv\Scripts\python.exe -m unittest discover -s .\backend\tests -p "test_*.py"`。前端收尾 `npm run build`。

禁止真实 Elsevier key、默认真网、把参考爬虫 key 写入本仓库 `.env`。

可选真网不作为合并条件：`DATA_ROOT` 指到临时目录，采 IP&M 某一年。不写正式库。

## 7. 当前进度

- [x] 调研 API 与官方入参
- [x] 确认按年采集、本期不做自动全文
- [x] 计划可实施
- [ ] 阶段 0-6

## 8. 计划偏差

无。

## 9. 验证结果

实现后填写。最低：相关后端测试通过；`npm run build` 通过。

## 10. 遗留问题

1. 真网验收年份实施时再定，不阻塞合并。
2. 是否关闭 IP&M 上的浏览器 `elsevier`，由用户在期刊配置处理。
3. 代理变量改名另开任务。
4. 国外全文另开计划。