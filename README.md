# Knowledge Vault

Knowledge Vault 是一个正在持续演进的个人知识库项目。它最初从文献管理出发，当前已经具备文献管理与期刊采集能力，后续会继续扩展到采集、整理、分析、沉淀与复用等更完整的知识工作流。

建议未来 GitHub 仓库名使用：`knowledge-vault`

## 当前能力

- 文献管理：文献条目、标签、文件夹、笔记、统计、备份
- 采集中心：按期刊配置采集源（国家哲社文献中心 / 期刊官网 / Scopus API / Elsevier）、按期或按年查询题录并按真实卷期入库、Magtech 官网全文 PDF 补采、翻译、JSON/Markdown 导出
- 论文分析：整期或从整个文献库检索自选论文创建异步综合分析，支持默认 Prompt 查看、自定义要求、可选 PDF 全文、运行历史与显式模型选择
- 模型平台：页面维护 Gemini Native / OpenAI Compatible 模型；论文分析、论文翻译和视频笔记在任务入口选择具体模型
- 视频转笔记：输入 B 站链接，自动执行音频下载、Whisper 转写和模型笔记生成
- 单一主项目结构：前后端与采集能力已统一到同一个仓库中维护

## 项目方向

Knowledge Vault 不再只定位为“文献管理系统”，而是一个面向个人研究与知识工作的工作台。后续重点会放在：

- 多来源内容采集
- 知识整理与结构化沉淀
- 分析、摘要与再利用
- 面向个人知识库的长期演进

## 技术栈

- 前端：React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + TanStack Router / Query + ECharts
- 后端：Flask + SQLAlchemy + SQLite
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + PyMuPDF4LLM + Docling + google-genai + openai

## 仓库结构

```text
.
├─ backend/
├─ frontend/
├─ docs/
├─ desktop.py
├─ desktop.bat
├─ start.bat
├─ stop.bat
├─ README.md
└─ AGENTS.md
```

## 快速开始

### 1. 安装依赖

前端要求 Node.js `^20.19.0` 或 `>=22.12.0`，使用 npm 与仓库内唯一锁文件 `frontend/package-lock.json`。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe --version
python -m pip --python .\.venv\Scripts\python.exe install -r .\backend\requirements.txt
cd .\frontend
npm install
cd ..
```

### 2. 初始化数据库

仓库随附 `backend/data/db/app.db`（含数据与迁移基线），可直接使用。全新环境（无数据库文件）时执行：

```powershell
cd .\backend
& ..\.venv\Scripts\python.exe -m flask --app run.py db upgrade head
cd ..
```

数据库结构变更统一通过 Flask-Migrate 管理（`flask db migrate` + `flask db upgrade`），不再依赖 `create_all()`。

### 3. 配置模型

启动系统后可从侧边栏 `System → 模型配置` 新增模型档案、填写 Base URL / 模型名称 / API Key。页面保存的 API Key 只写入根目录 `.env` 的 `LLM_API_KEYS_JSON`，不会进入数据库或 API 响应；使用大模型的任务在各自入口选择具体模型。

系统保留原有 Gemini Key 作为兼容回退，优先级如下：

1. 环境变量 `GEMINI_API_KEY`
2. 文件 `backend/gemini_api_key.txt`
3. 文件 `gemini_api_key.txt`

推荐只保留 `backend/gemini_api_key.txt`，并确保该文件不提交到 Git。
如果当前机器无法直连 `generativelanguage.googleapis.com:443`，可以在仓库根目录创建 `.env`，并配置：

```env
GEMINI_PROXY_URL=http://127.0.0.1:7890
```

也支持直接在 `.env` 中使用 `HTTPS_PROXY` 或 `HTTP_PROXY`。

国外期刊题录可使用 Scopus API。在「期刊与采集源」中填写期刊 ISSN 并启用 `Scopus API`，再到「Collection → 采集设置」保存 Elsevier Research Products API Key。密钥写入根目录 `.env` 的 `ELSEVIER_API_KEY`，不会进入数据库或 API 响应；Scopus 请求固定直连，不读取系统代理，COMPLETE 权益需要校园网或 aTrust 对应的出口 IP。

### 4. 启动与关闭

推荐使用桌面托盘启动器：

```bat
desktop.bat
```

双击后不会出现任何终端窗口：前后端在后台启动，托盘图标常驻右下角（首次运行自动安装启动器依赖 pystray / Pillow）。就绪后自动用默认浏览器打开界面；关闭浏览器页面不影响服务，右键托盘图标可选择「打开界面 / 重启服务 / 退出」，退出会按进程树彻底停止前后端。

备用的手工方式（会弹出终端窗口）：

```bat
start.bat
stop.bat
```

默认地址：

- 前端：`http://127.0.0.1:3000`
- 后端：`http://127.0.0.1:5000`
- 健康检查：`http://localhost:5000/api/health`

端口被其他程序占用时自动顺延（5000→5001…、3000→3001…），实际端口以托盘菜单显示为准；手工方式下后端会把实际端口打印到终端。桌面启动器单独使用 `KV_BACKEND_PORT` / `KV_FRONTEND_PORT` 环境变量注入端口。

### 5. 常用开发命令

```powershell
# 单独启动后端
cd .\backend
& ..\.venv\Scripts\python.exe .\run.py

# 单独启动前端
cd .\frontend
npm run dev

# 运行后端测试
& .\.venv\Scripts\python.exe -m unittest discover -s .\backend\tests -p "test_*.py"

# 前端构建验证
cd .\frontend
npm run build

# 前端完整质量检查
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
npm run check:chunks
npm run format:check
```

## 模块入口

- 文献管理：侧边栏 `Workspace`
- 论文分析：侧边栏 `Analysis → 论文分析`
- 采集中心：侧边栏 `Collection`
- 视频转笔记：侧边栏 `Media`
- 模型配置：侧边栏 `System`

视频转笔记模块除以上环境外，还需要本机具备：`yt-dlp`、FFmpeg、名为 `whisper` 的 conda 环境（内装 `faster-whisper`），并在创建任务时选择已配置 API Key 的模型。使用 Gemini 且本机无法直连时，还需在 `.env` 配置代理。该模块计划改为项目内部依赖，调整前会先确认方案。

视频转笔记模块的任务产物会保存到：

- `backend/data/artifacts/video-notes/<task_id>/source/`
- `backend/data/artifacts/video-notes/<task_id>/transcript/`
- `backend/data/artifacts/video-notes/<task_id>/notes/`
- `backend/data/artifacts/video-notes/<task_id>/metadata.json`

## 文档入口

- 当前架构：[`docs/current-architecture.md`](docs/current-architecture.md)
- 目标实现规范：[`docs/specifications/target-implementation-spec.md`](docs/specifications/target-implementation-spec.md)
- 决策记录：[`docs/decisions/project-decisions.md`](docs/decisions/project-decisions.md)
- 工程经验：[`docs/lessons/engineering-lessons.md`](docs/lessons/engineering-lessons.md)
- 文档导航：[`docs/documentation-map.md`](docs/documentation-map.md)
- 设计与实施计划：[`docs/plans/`](docs/plans/)

## 开发约定

- 仓库根目录就是唯一项目根目录，不再嵌套子项目根目录
- 新功能优先通过 API + Service 实现，不新增独立脚本式应用入口
- 采集原始结果先落 `raw_issue/raw_paper`，再做后续翻译、分析和导出
- 结构、运行方式、开发流程或产品方向发生变化时，要同步更新文档
