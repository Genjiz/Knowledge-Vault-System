# Knowledge Vault

Knowledge Vault 是一个正在持续演进的个人知识库项目。它最初从文献管理出发，当前已经具备文献管理与期刊采集能力，后续会继续扩展到采集、整理、分析、沉淀与复用等更完整的知识工作流。

建议未来 GitHub 仓库名使用：`knowledge-vault`

## 当前能力

- 文献管理：文献条目、标签、文件夹、笔记、统计、备份
- 采集中心：按期刊配置采集源（国家哲社文献中心 / 期刊官网 / Scopus API / Elsevier）、按期或按年查询题录并按真实卷期入库、Magtech 与授权 ScienceDirect 全文 PDF 补采、人工验证后续跑、翻译、JSON/Markdown 导出
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
- 采集与 AI：requests + beautifulsoup4 + DrissionPage + pywinauto + PyMuPDF4LLM + Docling + google-genai + openai

## 仓库结构

```text
.
├─ backend/
├─ frontend/
├─ docs/
├─ desktop.py
├─ desktop.bat
├─ README.md
└─ AGENTS.md
```

## 快速开始

### 1. 初始化环境

Windows x64 环境要求 Python `3.13.14`、Node.js `24.17.0` 和 npm `11.13.0`。先退出正在运行的 Knowledge Vault 前后端进程，再在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

脚本会创建或复用根目录 `.venv`、安装精确锁定的后端依赖、通过 `npm ci` 重建前端依赖、在缺少时由 `.env.example` 创建 `.env`、执行数据库迁移，并完成后端依赖检查和前端构建。`.venv/` 与 `frontend/node_modules/` 是本机生成目录，不由 Git 跟踪。

如果 Python 未加入 `PATH` 且尚未创建 `.venv`，可显式指定解释器：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -PythonExecutable "C:\Path\To\Python313\python.exe"
```

### 2. 初始化数据库

`setup.ps1` 已自动把数据库升级到仓库当前迁移版本。仓库随附 `backend/data/db/app.db`（含数据与迁移基线）；需要单独修复或升级数据库时执行：

```powershell
cd .\backend
& ..\.venv\Scripts\python.exe -m flask --app run.py db upgrade head
cd ..
```

数据库结构变更统一通过 Flask-Migrate 管理（`flask db migrate` + `flask db upgrade`），不再依赖 `create_all()`。

ScienceDirect 全文补采使用当前 Windows 用户的普通 Edge `Default` profile。开始任务前需在该 profile 中完成机构登录，并保持桌面解锁、Edge 可见且未最小化；自动下载期间会短暂占用前台焦点和鼠标。出现人机验证时任务会暂停，用户在同一 Edge 页面完成验证后可从界面继续。

### 3. 配置模型

启动系统后可从侧边栏 `System → 模型配置` 新增模型档案、填写 Base URL / 模型名称 / API Key。页面保存的 API Key 只写入根目录 `.env` 的 `LLM_API_KEYS_JSON`，不会进入数据库或 API 响应；使用大模型的任务在各自入口选择具体模型。

系统保留原有 Gemini Key 作为兼容回退，优先级如下：

1. 环境变量 `GEMINI_API_KEY`
2. 文件 `backend/gemini_api_key.txt`
3. 文件 `gemini_api_key.txt`

推荐只保留 `backend/gemini_api_key.txt`，并确保该文件不提交到 Git。
如果当前机器无法直连模型服务，可以在仓库根目录 `.env` 配置标准代理变量。以下端口是本机 Veee 示例，其他机器应填写代理客户端实际监听端口：

```env
HTTP_PROXY=http://127.0.0.1:15236
HTTPS_PROXY=http://127.0.0.1:15236
NO_PROXY=localhost,127.0.0.1,::1
```

Gemini 和 OpenAI Compatible 模型使用这些标准变量；Scopus、NCPSSD 与 Magtech 在应用层固定直连。完整的分流规则、Windows 系统代理与 TUN/aTrust 区别见 [`docs/proxy-and-network.md`](docs/proxy-and-network.md)。

国外期刊题录可使用 Scopus API。在「期刊与采集源」中填写期刊 ISSN 并启用 `Scopus API`，再到「Collection → 采集设置」保存 Elsevier Research Products API Key。密钥写入根目录 `.env` 的 `ELSEVIER_API_KEY`，不会进入数据库或 API 响应；Scopus 请求固定直连，不读取系统代理，COMPLETE 权益需要校园网或 aTrust 对应的出口 IP。

Scopus 题录含 PII 时，文献详情或卷期详情可尝试从 ScienceDirect 获取全文。下载只使用当前机构网络和浏览器会话已有的合法权限；遇到人机校验时任务暂停并打开可见浏览器，由用户手动处理后继续。Cloudflare 出口拒绝会提示先切换校园网或 aTrust/VPN，不会自动绕过。

### 4. 启动与关闭

推荐使用桌面托盘启动器：

```bat
desktop.bat
```

双击后不会出现任何终端窗口：前后端在后台启动，托盘图标常驻右下角（首次运行自动安装启动器依赖 pystray / Pillow）。就绪后自动用默认浏览器打开界面；关闭浏览器页面不影响服务，右键托盘图标可选择「打开界面 / 重启服务 / 退出」，退出会按进程树彻底停止前后端。

默认地址：

- 前端：`http://127.0.0.1:3000`
- 后端：`http://127.0.0.1:5000`
- 健康检查：`http://localhost:5000/api/health`

端口被其他程序占用时自动顺延（5000→5001…、3000→3001…），实际端口以托盘菜单显示为准。桌面启动器使用 `KV_BACKEND_PORT` / `KV_FRONTEND_PORT` 环境变量注入端口。

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
- 代理与网络：[`docs/proxy-and-network.md`](docs/proxy-and-network.md)
- 设计与实施计划：[`docs/plans/`](docs/plans/)

## 开发约定

- 仓库根目录就是唯一项目根目录，不再嵌套子项目根目录
- 新功能优先通过 API + Service 实现，不新增独立脚本式应用入口
- 采集原始结果先落 `raw_issue/raw_paper`，再做后续翻译、分析和导出
- 结构、运行方式、开发流程或产品方向发生变化时，要同步更新文档
