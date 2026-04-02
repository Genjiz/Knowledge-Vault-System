# 爬虫整合与采集中心设计文档

## 背景

当前仓库中存在两个相互独立的项目：

- `Knowledge Vault`
  - 现有主系统
  - 技术栈为 `Flask + SQLAlchemy + SQLite + Vue 3 + Vite + Element Plus`
  - 已具备清晰的前后端分离结构
- `爬虫`
  - 独立的采集与分析工具
  - 技术栈为 `Python + Streamlit + 脚本 + 本地 JSON/Markdown 文件`
  - 页面逻辑、文件读写、子进程调用和 AI 处理耦合较重

本次目标不是简单拼接两个项目，而是将“爬虫”的能力重构为 `Knowledge Vault` 中可维护、可扩展的正式业务模块。

## 目标

- 将 `爬虫` 的功能完整整合到 `Knowledge Vault`
- 最终统一为单一 `Vue + Flask API` 架构
- 采集、浏览、翻译、分析全部纳入主系统
- 原始采集结果先保留在原始数据域，不直接导入正式文献域
- 保留 `JSON` 与 `Markdown` 文件产物，但它们不再是主数据源
- 为后续“人工确认后导入正式文献”保留自然扩展路径

## 非目标

- 本阶段不实现“raw 数据导入正式文献”功能
- 本阶段不升级数据库到 MySQL/PostgreSQL
- 本阶段不引入独立任务队列基础设施
- 本阶段不保留 Streamlit 作为最终交付界面

## 设计原则

1. 主系统只保留一个正式 UI：Vue
2. 主数据只保留一个权威存储：SQLite 数据库
3. `JSON` 和 `Markdown` 作为派生产物，而非系统内部主链路
4. 采集、翻译、分析必须通过后端 service / provider 组织，不能散落在页面中
5. 新能力作为独立子域建设，而不是零散塞入现有模块
6. 视觉设计和架构设计同时定型，避免后续返工

## 总体架构

整合后的系统保持单仓库、单应用，但内部新增“采集中心”子域：

- 前端
  - 仍使用 Vue Router、Pinia、Element Plus
  - 新增“采集中心”相关页面
- 后端
  - 仍使用 Flask 应用工厂和 SQLAlchemy
  - 新增 crawler 子域，承载采集任务、原始期号、原始论文、分析结果
- 存储
  - 继续使用 `backend/app.db`
  - 所有新数据表先进入同一个 SQLite 数据库
- 产物
  - 统一导出标准化 `JSON` 和 `Markdown`
  - 导出文件集中存放到 `backend/artifacts/`

## 后端模块设计

建议在 `backend/app/` 下新增 crawler 子域。推荐目录：

```text
backend/app/
  crawler/
    __init__.py
    models/
    providers/
    services/
    schemas/
    repositories/
    routes/
```

### 模块职责

- `models`
  - 定义采集任务、原始期号、原始论文、分析结果等数据模型
- `providers`
  - 封装国内期刊采集、国外期刊采集、翻译、分析等外部能力
  - 采用 Python 类或函数接口，直接返回结构化对象
- `services`
  - 编排业务流程
  - 负责调用 provider、保存数据库、生成导出产物、写日志、处理状态流转
- `repositories`
  - 封装复杂查询和持久化操作
- `routes`
  - 提供前端 API
- `schemas`
  - 负责请求参数和响应结构约束

## 数据模型设计

建议新增以下核心实体。

### `crawl_task`

用途：记录一次采集、翻译或分析任务。

建议字段：

- `id`
- `task_type`
- `source_type`
- `journal_name`
- `year`
- `issue`
- `status`
- `progress_message`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

### `crawl_task_log`

用途：保存任务执行日志，替代当前 Streamlit 页面的实时控制台输出。

建议字段：

- `id`
- `task_id`
- `level`
- `message`
- `created_at`

### `raw_issue`

用途：保存期号级原始抓取结果。

建议字段：

- `id`
- `source_type`
- `journal_name`
- `journal_slug`
- `year`
- `issue`
- `language`
- `crawl_task_id`
- `translation_status`
- `analysis_status`
- `paper_count`
- `raw_json_path`
- `created_at`
- `updated_at`

建议加唯一约束：`source_type + journal_name + year + issue`

### `raw_paper`

用途：保存文章级原始记录。

建议字段：

- `id`
- `raw_issue_id`
- `source_identifier`
- `title`
- `title_zh`
- `authors`
- `abstract`
- `abstract_zh`
- `keywords_json`
- `pages`
- `detail_url`
- `published_at`
- `sort_index`
- `translation_status`
- `created_at`
- `updated_at`

### `raw_issue_analysis`

用途：保存期号级分析结果。

建议字段：

- `id`
- `raw_issue_id`
- `model_name`
- `prompt_version`
- `content_markdown`
- `artifact_md_path`
- `status`
- `error_message`
- `created_at`
- `updated_at`

### `llm_run`

用途：审计翻译与分析调用。

建议字段：

- `id`
- `run_type`
- `target_type`
- `target_id`
- `model_name`
- `status`
- `error_message`
- `started_at`
- `finished_at`

## 数据流设计

### 采集

1. 前端提交采集参数
2. 后端创建 `crawl_task`
3. service 调用相应 provider 采集
4. provider 返回结构化 `issue + papers`
5. service 将数据写入 `raw_issue` 和 `raw_paper`
6. service 导出标准化 `JSON`
7. 更新任务状态并记录日志

### 翻译

1. 前端对某个 `raw_issue` 或单篇 `raw_paper` 发起翻译
2. 后端创建翻译任务
3. 翻译 provider 返回翻译结果
4. service 更新数据库中的中文字段和状态
5. service 重新生成标准化 `JSON`

### 分析

1. 前端对某个 `raw_issue` 发起分析
2. 后端创建分析任务
3. 分析 provider 基于 `raw_paper` 数据生成 Markdown
4. service 写入 `raw_issue_analysis`
5. service 导出 `.md`

## JSON / Markdown 策略

改造后仍然保留文件产物，但其角色变更为归档和交换格式。

### 原则

- 数据库为权威主存储
- `JSON` 为原始期号快照
- `Markdown` 为分析快照
- 任何页面展示都优先读取数据库，而不是直接读文件

### 建议目录

```text
backend/artifacts/
  raw-json/<source>/<journal>/<year>/<issue>.json
  analysis-md/<source>/<journal>/<year>/<issue>.md
```

### 保留原因

- 便于独立下载、离线处理和二次分析
- 便于与外部脚本或知识库系统对接
- 便于审计与人工排查

## 前端设计

### 模块定位

新增一级模块“采集中心”，替代原 Streamlit 三页应用。

### 页面结构

#### 1. 采集任务页

职责：

- 选择数据源、期刊、年份、期号
- 发起采集任务
- 展示任务状态、进度、最近日志

#### 2. 原始期号列表页

职责：

- 浏览 `raw_issue`
- 按来源、期刊、年份、期号、翻译状态、分析状态筛选
- 跳转到期号详情

#### 3. 原始期号详情页

职责：

- 查看该期号下的 `raw_paper`
- 触发整期翻译
- 查看/下载 JSON 产物

#### 4. 原始论文详情抽屉或详情页

职责：

- 展示标题、摘要、关键词、链接等字段
- 支持单篇翻译

#### 5. 分析页

职责：

- 查看 `raw_issue_analysis`
- 生成/重生成分析
- 下载 Markdown

## API 设计

建议新增以下资源型 API：

- `POST /api/crawl-tasks`
- `GET /api/crawl-tasks`
- `GET /api/crawl-tasks/<id>`
- `GET /api/crawl-tasks/<id>/logs`
- `GET /api/raw-issues`
- `GET /api/raw-issues/<id>`
- `GET /api/raw-issues/<id>/papers`
- `POST /api/raw-issues/<id>/translate`
- `POST /api/raw-papers/<id>/translate`
- `GET /api/raw-papers/<id>`
- `GET /api/raw-issues/<id>/analysis`
- `POST /api/raw-issues/<id>/analyze`
- `GET /api/raw-issues/<id>/artifacts`

## 任务执行策略

本阶段先采用应用内异步任务思路，但接口设计不要锁死为同步模式。

### 原则

- 采集、翻译、分析都建任务记录
- 所有长耗时操作都返回任务 ID
- 前端通过轮询获取状态
- 后续可以无痛迁移到 worker / queue

## 错误处理

错误需要分层记录：

- 任务级
  - 参数错误、站点不可达、浏览器环境异常
- 数据级
  - 期号结构不完整、字段缺失、重复期号
- AI 级
  - API 密钥错误、额度不足、模型返回异常

要求：

- 错误必须落任务记录
- 可展示给前端的错误要可读
- 不因翻译或分析失败而丢失原始采集结果

## 视觉系统

整个项目的视觉方向采用“精致科技杂志风”。

### 目标气质

- 高级
- 理性
- 轻未来感
- 可长时间阅读与操作

### 视觉规则

- 以深墨蓝、雾白、银灰为主色
- 以偏青高亮色做状态强调
- 使用更有识别度的标题字体和稳定正文字体组合
- 页面背景使用低强度渐变、细网格或局部光晕增强层次
- 组件靠边框、材质感、精细间距和状态反馈建立品质感
- 避免通用蓝白后台风和过度玻璃拟态

### 页面风格要求

- 仪表盘像研究控制台
- 采集任务页像任务编排台
- 原始结果页像结构化档案库
- 分析页像研究简报阅读器

## 迁移策略

本次选择直接朝目标架构重构，而不是保留 Streamlit 双入口。

迁移原则：

- 不保留 Streamlit 作为最终运行方式
- 不以 JSON 文件作为主业务链路
- 将爬虫、翻译、分析能力改造成后端原生 provider/service
- 若原项目已有可复用逻辑，则提炼其核心实现，但输出必须改为结构化对象

## 风险与应对

### 风险 1：国外期刊采集依赖浏览器环境

应对：

- 将浏览器能力封装在 provider 内
- 把环境检查、错误提示和日志落到任务系统

### 风险 2：历史脚本耦合高

应对：

- 先按 provider 边界拆分职责
- 再逐步清理目录依赖、文件依赖和 CLI 依赖

### 风险 3：SQLite 承载能力有限

应对：

- 本阶段接受
- 模型和仓储层设计保持可迁移性

## 分阶段实施建议

1. 新建 crawler 子域数据模型与 API 骨架
2. 打通国内/国外采集到数据库和 JSON 导出
3. 打通原始结果浏览页面
4. 打通翻译与分析到数据库和 Markdown 导出
5. 重构首页和采集中心的视觉系统
6. 为后续正式文献导入预留映射层

## 结论

本方案将 `爬虫` 的能力完整吸纳进 `Knowledge Vault`，以单一前后端分离架构、数据库主存储、文件派生产物和精致科技杂志风视觉系统作为最终形态。这样既能满足当前功能整合，也能为后续新增数据源、导入正式文献和升级基础设施提供清晰演进路径。

## 附录：现有爬虫输入输出调查

这一附录用于约束后续 provider 和 service 的重构边界，避免遗漏历史能力。

### 国内期刊采集入口

入口脚本：

- `爬虫/国内期刊爬虫/0.journal_paper_info_crawler.py`

当前参数形式：

- CLI 模式：`journal_name year issue`
- 交互模式：依次输入期刊名、年份、期数

当前主流程：

1. `1.journal_url_finder.py` 查期刊 URL
2. `2.issue_url_finder.py` 查期号 URL
3. `3.paper_title_extractor.py` 提取论文标题并首次落盘 JSON
4. `4.paper_detail_url_finder.py` 回写论文详情链接
5. `5.paper_detail_info_extractor.py` 回写摘要、关键词等详情信息

当前返回的核心结构：

- 期号级字段
  - `journal_name`
  - `year`
  - `issue`
  - `issue_url`
  - `issue_method`
  - `papers_count`
  - `saved_path`
  - `success`
  - `error_message`
  - `steps`
- 论文级字段
  - `title`
  - `authors`
  - `pages`
  - `issue`
  - 详情回填后的 `detail_url`
  - 详情回填后的 `abstract`
  - 详情回填后的 `keywords`

当前文件产物：

- 原始数据 JSON：`<项目根>/<期刊>/<年份>/<期刊>_<年份>_<期号>.json`
- 辅助缓存：
  - `爬虫/国内期刊爬虫/journal_url_cache.json`
  - `爬虫/国内期刊爬虫/issue_url_cache.json`

重构时必须保留的输入输出能力：

- 输入：`source_type=domestic`、期刊、年份、期号
- 输出：一个结构化 `issue` 对象和一组 `paper` 对象
- 日志：每个阶段的成功/失败信息

### 国外期刊采集入口

入口脚本：

- `爬虫/国外期刊爬虫/0.main_crawler.py`

当前参数形式：

- CLI 模式：`journal_name year issue`
- 交互模式：输入期刊名、年份、期号
- `issue` 当前支持字符串，例如 `"Part A"`

当前主流程：

1. `1.vol_year_mapper.py` 计算年份对应卷号
2. `config_foreign.py` 生成 ScienceDirect 期号 URL
3. `2.issue_crawler.py` 使用 DrissionPage 打开期号页并提取文章
4. 初始化 `title_zh` 和 `abstract_zh` 为空字符串
5. 落盘 JSON

当前返回或落盘的核心结构：

- 期号级字段
  - `journal_name`
  - `year`
  - `volume`
  - `issue`
  - `source_url`
  - `total_count`
- 论文级字段
  - `title`
  - `authors`
  - `detail_url`
  - `abstract`
  - `title_zh`
  - `abstract_zh`

当前文件产物：

- 原始数据 JSON：`<项目根>/<期刊>/<年份>/<期刊>_<年份>_<期号>.json`
- 辅助缓存：
  - `爬虫/国外期刊爬虫/journal_vol_cache.json`
  - `爬虫/dp_browser_data/`
- 调试日志：
  - `mapper_debug.log`

重构时必须保留的输入输出能力：

- 输入：`source_type=foreign`、期刊、年份、期号字符串
- 输出：一个结构化 `issue` 对象和一组 `paper` 对象
- 环境检查：浏览器端口、用户数据目录、抓取失败原因

### 翻译入口

入口脚本：

- `爬虫/国外期刊爬虫/3.translator.py`

当前参数形式：

- `--file <json路径>`
- 或 `--journal <期刊> --year <年份> --issue <期号>`

当前处理方式：

- 读取 JSON 文件中的 `papers`
- 调用 Gemini
- 回写每篇论文的：
  - `title_zh`
  - `abstract_zh`
- 再次覆盖写回原 JSON 文件

重构时必须保留的输入输出能力：

- 输入：期号级翻译和单篇翻译两种入口
- 输出：更新后的中文标题和中文摘要
- 审计：模型名、失败原因、时间戳

### 分析入口

入口脚本：

- `爬虫/journal_paper_analyzer.py`
- Streamlit 页面中也存在一份等价分析流程：`爬虫/pages/3_📊_Analysis.py`

当前参数形式：

- Python 函数调用形式为主
- 依赖期刊名、年份、期号从 JSON 中读回论文数据

当前处理方式：

- 从 JSON 读取 `papers`
- 将标题、摘要、关键词整理成 prompt
- 调用 Gemini 流式生成分析结果
- 输出到 `<项目根>/<期刊>/<年份>/<期刊>_<年份>_<期号>.md`

当前文件产物：

- 分析 Markdown：`<项目根>/<期刊>/<年份>/<期刊>_<年份>_<期号>.md`

重构时必须保留的输入输出能力：

- 输入：基于某个 `raw_issue` 的整期分析
- 输出：数据库中的 Markdown 内容和对应导出文件
- 能够重新生成并覆盖旧分析版本

### 当前文件驱动链路总结

现有项目的实际主链路是：

1. 采集脚本写 JSON
2. 翻译脚本读 JSON 再回写 JSON
3. 分析脚本读 JSON 再生成 Markdown
4. Streamlit 页面直接围绕文件系统工作

目标架构重构后，必须改为：

1. provider 直接返回结构化对象
2. service 先写数据库
3. artifact service 再生成 JSON / Markdown
4. Vue 页面与 Flask API 只围绕数据库与任务状态工作

