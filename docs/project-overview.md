# Project Overview

## 项目定位

`Knowledge Vault` 是一个面向个人研究与知识工作的长期项目。

它已经不再局限于“文献管理系统”这个范围，而是在现有文献管理与期刊采集能力的基础上，逐步发展为一个更完整的个人知识库，包括：

- 采集
- 整理
- 分析
- 沉淀
- 再利用

## 当前范围

当前代码库主要覆盖三条能力线：

### 1. 文献管理

- 文献条目
- 标签
- 文件夹
- 笔记
- 统计
- 备份与恢复

### 2. 采集中心

- 国内/国外期刊采集
- 原始期号入库
- 原始论文入库
- 翻译
- 分析
- JSON / Markdown 派生产物导出

### 3. 视频转笔记

- 输入 B 站视频链接
- 下载音频
- 生成 SRT 字幕
- 调用 Gemini 生成 Markdown 笔记
- 保存中间产物与任务日志

## 架构概览

### 前端

- Vue 3 + Vite
- Vue Router
- Pinia
- Element Plus
- ECharts

### 后端

- Flask
- SQLAlchemy
- SQLite

### 采集与 AI

- requests
- beautifulsoup4
- DrissionPage
- google-genai

## 后端结构约定

采集相关后端遵循分层设计：

- `models`：数据模型
- `repositories`：数据访问
- `services`：业务编排
- `providers`：采集、翻译、分析能力适配
- `routes`：HTTP API
- `runtime`：运行时路径、环境与能力装配

## 数据与产物

主数据库：

- `backend/app.db`

采集核心表：

- `crawl_task`
- `crawl_task_log`
- `raw_issue`
- `raw_paper`
- `raw_issue_analysis`
- `llm_run`

派生产物目录：

- `backend/artifacts/raw-json/`
- `backend/artifacts/analysis-md/`

原则：

- 数据库是主存储
- JSON/Markdown 是派生产物，用于重跑、审计、导出与复核

## 目录结构

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ video_notes/
│  ├─ artifacts/
│  ├─ requirements.txt
│  └─ run.py
├─ frontend/
│  ├─ src/
│  └─ package.json
├─ docs/
│  ├─ plans/
│  ├─ documentation-map.md
│  ├─ project-overview.md
│  ├─ development-guide.md
│  ├─ roadmap.md
│  └─ project-log.md
├─ start.bat
└─ stop.bat
```

## 重要约束

- 仓库根目录就是唯一项目根目录
- 不再使用 `literature-manager/` 作为嵌套子项目目录
- 新能力优先接入现有前后端架构
- 项目正在从“文献管理”向“个人知识库”演进，命名、文档和设计都应服务这个方向
- 学术文献管理、期刊采集总结、视频转笔记是独立模块，不强行共用一个“文献/笔记”业务模型
