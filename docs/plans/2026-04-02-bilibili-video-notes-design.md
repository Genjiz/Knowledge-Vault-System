# Bilibili Video Notes Module Design

## 背景

Knowledge Vault 当前正在从单一的文献管理项目演进为多个独立能力模块组成的个人知识库系统。

目前已经明确存在三个独立模块：

- 学术文献管理
- 采集期刊论文标题摘要并生成总结
- 根据视频生成笔记

本次要新增的是第三个模块：`视频转笔记`。它是一个独立模块，不属于现有“文献/笔记”业务模型，也不需要在短期内与其他模块做跨模块连接。

用户已经准备好本地依赖环境，并提供了现有手工工作流文档 [`B 站视频转笔记工作流.md`](../../B%20站视频转笔记工作流.md)。目标是把这套流程正式接入系统，使用户在网页中输入 B 站视频链接后，系统能够自动完成：

1. 下载音频
2. 转写 SRT
3. 调用 Gemini 生成最终 Markdown 笔记

同时保留中间产物与任务日志，方便查看、下载、排错和重试。

## 目标

- 新增一个独立的 `视频转笔记` 模块
- 前端提供独立页面，支持准备说明、创建任务、查看任务列表、查看任务详情
- 后端提供独立 API、任务模型、日志模型和执行服务
- 自动调用本机 `yt-dlp` 与 `conda run -n whisper ...` 完成下载与转写
- 调用 Gemini 根据 SRT 生成最终 Markdown 笔记
- 在项目内保存中间产物与最终笔记
- 对失败任务保留现场，便于排查

## 非目标

- 不把视频笔记写入当前“文献管理”或“笔记”业务表
- 不做跨模块连接
- 第一版不做任务取消
- 第一版不做从单一步骤恢复执行
- 第一版不做批量任务
- 第一版不引入 Celery / Redis 之类的完整任务队列基础设施

## 模块边界

`视频转笔记` 是独立模块，不属于现有文献模块，也不属于现有采集期刊模块。它拥有自己的：

- 页面入口
- API
- 任务记录
- 日志记录
- 文件产物目录

与其他模块的关系仅限于共用项目基础设施，例如：

- Flask 应用
- SQLite
- 通用响应格式
- Gemini 运行时能力
- 前端整体布局与路由系统

## 前端设计

### 路由

新增三类页面：

- `/video-notes`
  - 模块首页
  - 展示准备工作说明
  - 提供新建任务表单
  - 展示最近任务摘要
- `/video-notes/tasks`
  - 任务列表页
  - 展示所有任务、状态、当前步骤、更新时间
- `/video-notes/tasks/:id`
  - 任务详情页
  - 展示任务元数据、步骤进度、日志、中间产物、最终 Markdown 笔记

### 模块首页

首页同时承担“说明页”和“发起任务页”功能。

主要包含：

- 模块介绍
- 准备工作说明
  - FFmpeg
  - `yt-dlp`
  - `whisper` conda 环境
  - 代理提醒
  - Gemini Key 提醒
- 新建任务表单
  - `source_url`
  - `whisper_model`
  - `language`
  - `device`
  - `compute_type`
  - `use_vad`
- 最近任务摘要

准备说明不会简单原样粘贴工作流文档，而是整理为更适合页面展示的结构化说明。

### 任务列表页

任务列表页展示：

- 视频标题
- `bvid`
- 原始链接
- 状态
- 当前步骤
- 最近更新时间
- 错误摘要

第一版以“可看清任务状态”为主，不做复杂筛选和批量操作。

### 任务详情页

任务详情页展示：

- 基本信息
  - 视频标题
  - `bvid`
  - 原始 URL
  - 创建时间
  - 执行参数
- 进度信息
  - 大状态
  - 当前步骤
  - 进度说明
- 中间产物
  - 音频文件
  - SRT 字幕
  - 元数据 JSON
- 最终产物
  - Markdown 笔记预览
  - 下载按钮
- 日志时间线

### 第一版交互范围

保留：

- 新建任务
- 查看列表
- 查看详情
- 查看 / 下载产物
- 整任务重试

暂不实现：

- 删除任务
- 取消任务
- 从某一步继续执行
- 单独重跑 Gemini
- 批量创建任务

## 后端设计

### 子域结构

新增独立子域：

```text
backend/app/video_notes/
├─ models/
├─ repositories/
├─ routes/
├─ runtime/
└─ services/
```

与现有 crawler 子域保持同样的分层风格。

### 数据模型

建议新增两张表：

#### 1. `video_note_task`

字段建议：

- `source_url`
- `platform`
- `bvid`
- `video_title`
- `status`
- `current_step`
- `progress_message`
- `error_message`
- `whisper_model`
- `language`
- `device`
- `compute_type`
- `use_vad`
- `audio_path`
- `transcript_path`
- `note_path`
- `metadata_path`
- `started_at`
- `finished_at`

说明：

- `platform` 第一版固定为 `bilibili`
- 完整字幕与完整笔记不直接存进数据库，而是保存到文件系统

#### 2. `video_note_task_log`

字段建议：

- `task_id`
- `level`
- `message`

用于记录任务全过程日志。

### 任务状态

任务状态分两层：

#### 大状态 `status`

- `pending`
- `running`
- `completed`
- `failed`

#### 当前步骤 `current_step`

- `download_audio`
- `transcribe_srt`
- `generate_note`
- `done`

同时记录：

- `progress_message`
- `error_message`

## 执行链路

### 总体方式

采用“任务式后台执行”而不是同步 HTTP 直跑。

流程：

1. 前端创建任务
2. 后端立即返回任务 ID
3. 后台线程或轻量执行器异步执行任务
4. 前端通过列表页 / 详情页查看状态

这样可以避免长时间 HTTP 阻塞，更适合下载、转写、生成笔记这类耗时流程。

### 步骤 1：创建任务

- 校验输入 URL
- 解析 `bvid`
- 写入任务记录
- 初始状态为 `pending`

### 步骤 2：下载音频

- 状态改为 `running`
- `current_step = download_audio`
- 调用 `yt-dlp`
- 输出音频到任务目录下的 `source/`
- 写日志
- 成功后记录 `audio_path`

### 步骤 3：转写字幕

- `current_step = transcribe_srt`
- 调用 `conda run -n whisper python <项目内脚本>`
- 输出 `.srt` 到 `transcript/`
- 写日志
- 成功后记录 `transcript_path`

### 步骤 4：生成笔记

- `current_step = generate_note`
- 读取 SRT
- 组装提示词
- 调用 Gemini
- 输出 Markdown 到 `notes/`
- 写日志
- 成功后记录 `note_path`

### 步骤 5：收尾

- 输出 `metadata.json`
- 状态改为 `completed`
- `current_step = done`
- 记录 `finished_at`

### 失败处理

任一步失败时：

- 写错误日志
- `status = failed`
- 更新 `error_message`
- 记录 `finished_at`
- 不清理已经生成的中间产物

## 标题策略

视频标题策略已确认如下：

- 优先从 `yt-dlp` 获取视频标题
- 如果拿不到标题，不视为任务失败
- 回退为 `bvid + url`

这样既保证任务可以持续执行，也保证任务列表与详情页始终有可展示的标题字段。

## 文件落盘规则

采用按任务 ID 建目录的方式，而不是按 `bvid` 建目录。

原因：

- 同一个视频可能重复生成
- 不同参数会产生不同结果
- 以后重试 / 重跑时更容易区分任务实例

目录建议如下：

```text
backend/artifacts/video-notes/<task_id>/
├─ source/
│  └─ video.wav
├─ transcript/
│  └─ video.srt
├─ notes/
│  └─ final-note.md
└─ metadata.json
```

### `metadata.json`

建议包含：

- 任务 ID
- 平台
- 原始 URL
- `bvid`
- 视频标题
- 创建时间
- 执行参数
- 产物路径
- 最终状态

## 命令执行与运行时

建议把外部命令调用封装在独立 runtime / service 中，而不是直接写在 route 中。

至少包含三类能力：

- `yt-dlp` 下载器
- whisper 转写执行器
- Gemini 笔记生成器

这样可以：

- 更好地单元测试
- 在失败时更清楚地定位问题
- 让 route 层保持轻量

## API 设计

第一版建议提供以下接口：

- `POST /api/video-note-tasks`
  - 创建任务
- `GET /api/video-note-tasks`
  - 获取任务列表
- `GET /api/video-note-tasks/<id>`
  - 获取任务详情
- `GET /api/video-note-tasks/<id>/logs`
  - 获取任务日志

第一版暂不提供：

- 删除任务
- 取消任务
- 从某一步重跑
- 单独重跑 Gemini

## 错误分类

建议明确区分以下错误类型：

- 输入错误
  - URL 非法
  - 无法解析 `bvid`
- 命令缺失
  - `yt-dlp` 不存在
  - `conda` 不存在
- 转写失败
  - whisper 环境损坏
  - 模型下载失败
  - CUDA / cuDNN 错误
- AI 生成失败
  - Gemini Key 缺失
  - 调用失败
  - 超时

每种失败都要落到：

- `error_message`
- 任务日志
- 最终 `failed` 状态

## 测试策略

第一版建议覆盖：

- URL / `bvid` 解析
- 任务创建默认值
- 状态流转
- 标题 fallback 逻辑
- 目录与文件路径生成规则
- `metadata.json` 内容生成
- Gemini 提示词组装
- 失败时状态与错误信息落库

涉及外部命令执行的测试应使用 mock，不真实调用 `yt-dlp` 和 whisper。

真实全流程验证使用手动测试完成。

## 风险与取舍

### 为什么不用同步 HTTP 执行

因为流程长、易超时，也不利于前端展示步骤进度。

### 为什么不用通用任务平台

因为当前目标明确且边界清晰，先把视频转笔记模块独立做好，比一开始做通用平台更稳。

### 为什么不用数据库存完整字幕和笔记

因为文件更适合保存大文本产物，也与现有 `artifacts` 思路一致。

## 结论

第一版应实现一个独立的“视频转笔记”模块，使用后台任务方式自动执行 `yt-dlp -> whisper -> Gemini` 流程，把中间产物和最终笔记保存在项目内的独立目录中，并通过任务列表与详情页向用户展示进度、日志和结果。
