# Development Guide

## 环境要求

- Python `3.11+`
- Node.js `18+`
- Windows 下可用的 Chrome/Chromium

补充说明：

- `DrissionPage` 依赖本机浏览器环境
- 默认浏览器 profile 目录为 `.crawler-browser-profile/`
- 视频转笔记模块需要本机可执行的 `yt-dlp`
- 视频转笔记模块需要名为 `whisper` 的 conda 环境，并且其中已安装 `faster-whisper`

## 首次安装

在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe --version
python -m pip --python .\.venv\Scripts\python.exe install -r .\backend\requirements.txt
cd .\frontend
npm install
cd ..
```

## Gemini 配置

Gemini API Key 读取优先级：

1. 环境变量 `GEMINI_API_KEY`
2. 文件 `backend/gemini_api_key.txt`
3. 文件 `gemini_api_key.txt`

推荐只保留：

- `backend/gemini_api_key.txt`
- 如果当前机器无法直连 `generativelanguage.googleapis.com:443`，可以在仓库根目录创建 `.env`
- 推荐在 `.env` 中配置 `GEMINI_PROXY_URL=http://127.0.0.1:7890`
- 也支持在 `.env` 中配置 `HTTPS_PROXY` 或 `HTTP_PROXY`

文件中只放 API Key 原文，不要附加说明文字。

## 启动与关闭

### 一键启动

```bat
start.bat
```

### 一键关闭

```bat
stop.bat
```

默认地址：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:5000`
- 健康检查：`http://localhost:5000/api/health`

## 常用开发命令

### 单独启动后端

```powershell
cd .\backend
& ..\.venv\Scripts\python.exe .\run.py
```

### 单独启动前端

```powershell
cd .\frontend
npm run dev
```

### 运行后端测试

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s .\backend\tests -p "test_*.py"
```

### 运行前端构建验证

```powershell
cd .\frontend
npm run build
```

## 视频转笔记模块运行要求

- 已安装 `yt-dlp`
- 已安装 FFmpeg
- 已存在 `whisper` conda 环境
- `whisper` 环境中可执行项目内脚本 `backend/app/video_notes/runtime/transcribe_audio.py`
- Gemini Key 已配置
- 当前机器可访问 `generativelanguage.googleapis.com:443`，或已在 `.env` 中配置 `GEMINI_PROXY_URL` / `HTTPS_PROXY` / `HTTP_PROXY`

相关人工工作流参考：

- `B 站视频转笔记工作流.md`

## 与目录结构相关的运行细节

- 仓库根目录是项目根目录
- 运行时路径工具会从当前代码位置向上寻找同时包含 `backend/` 和 `frontend/` 的目录
- 采集历史脚本位于 `backend/app/crawler/legacy/`
- JSON / Markdown 派生产物位于 `backend/artifacts/`
- 视频转笔记任务产物位于 `backend/artifacts/video-notes/`

## 文档维护要求

- 改动结构、脚本、配置或工作流时，同步更新对应文档
- 大一点的任务先在 `docs/plans/` 写方案或实施计划
- 重要决策完成后，补一条到 `docs/project-log.md`
