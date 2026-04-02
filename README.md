# Knowledge Vault

Knowledge Vault 是一个正在持续演进的个人知识库项目。它最初从文献管理出发，当前已经具备文献管理与期刊采集能力，后续会继续扩展到采集、整理、分析、沉淀与复用等更完整的知识工作流。

建议未来 GitHub 仓库名使用：`knowledge-vault`

## 当前能力

- 文献管理：文献条目、标签、文件夹、笔记、统计、备份
- 采集中心：期刊采集任务、原始期号入库、原始论文入库、翻译、分析、JSON/Markdown 导出
- 视频转笔记：输入 B 站链接，自动执行音频下载、Whisper 转写和 Gemini 笔记生成
- 单一主项目结构：前后端与采集能力已统一到同一个仓库中维护

## 项目方向

Knowledge Vault 不再只定位为“文献管理系统”，而是一个面向个人研究与知识工作的工作台。后续重点会放在：

- 多来源内容采集
- 知识整理与结构化沉淀
- 分析、摘要与再利用
- 面向个人知识库的长期演进

## 技术栈

- 前端：Vue 3 + Vite + Vue Router + Pinia + Element Plus + ECharts
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + google-genai

## 仓库结构

```text
.
├─ backend/
├─ frontend/
├─ docs/
├─ start.bat
├─ stop.bat
├─ README.md
└─ AGENTS.md
```

## 快速开始

### 1. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe --version
python -m pip --python .\.venv\Scripts\python.exe install -r .\backend\requirements.txt
cd .\frontend
npm install
cd ..
```

### 2. 配置 Gemini Key

优先级如下：

1. 环境变量 `GEMINI_API_KEY`
2. 文件 `backend/gemini_api_key.txt`
3. 文件 `gemini_api_key.txt`

推荐只保留 `backend/gemini_api_key.txt`，并确保该文件不提交到 Git。
如果当前机器无法直连 `generativelanguage.googleapis.com:443`，可以在仓库根目录创建 `.env`，并配置：

```env
GEMINI_PROXY_URL=http://127.0.0.1:7890
```

也支持直接在 `.env` 中使用 `HTTPS_PROXY` 或 `HTTP_PROXY`。

### 3. 启动与关闭

```bat
start.bat
stop.bat
```

默认地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:5000`
- 健康检查：`http://localhost:5000/api/health`

## 模块入口

- 文献管理：侧边栏 `Workspace`
- 采集中心：侧边栏 `Collection`
- 视频转笔记：侧边栏 `Media`

视频转笔记模块的任务产物会保存到：

- `backend/artifacts/video-notes/<task_id>/source/`
- `backend/artifacts/video-notes/<task_id>/transcript/`
- `backend/artifacts/video-notes/<task_id>/notes/`
- `backend/artifacts/video-notes/<task_id>/metadata.json`

## 文档入口

- 项目总览：[`docs/project-overview.md`](docs/project-overview.md)
- 开发指南：[`docs/development-guide.md`](docs/development-guide.md)
- 路线图：[`docs/roadmap.md`](docs/roadmap.md)
- 项目日志：[`docs/project-log.md`](docs/project-log.md)
- 文档导航：[`docs/documentation-map.md`](docs/documentation-map.md)
- 历史方案与实施文档：[`docs/plans/`](docs/plans/)

## 开发约定

- 仓库根目录就是唯一项目根目录，不再嵌套子项目根目录
- 新功能优先通过 API + Service 实现，不新增独立脚本式应用入口
- 采集原始结果先落 `raw_issue/raw_paper`，再做后续翻译、分析和导出
- 结构、运行方式、开发流程或产品方向发生变化时，要同步更新文档
