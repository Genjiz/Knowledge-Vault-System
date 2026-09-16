# 视频转笔记剥离包

本目录保存 2026-09-16 从 Knowledge Vault 主项目剥离的“视频转笔记”和“视频任务列表”实现。目录按原项目相对路径组织，便于后续整体移出仓库。

## 内容

- `backend/app/video_notes/`：模型、仓储、服务、路由和运行时实现。
- `backend/tests/video_notes/`：后端专项测试；未在剥离后重新验证。
- `frontend/src/features/video/pages.tsx`：视频任务创建、列表和详情页面。
- `frontend/e2e/video-notes.fragment.ts`：从共享 E2E 文件抽出的 fixture、接口 mock、路由和交互测试片段。
- `docs/plans/`：原始设计与实施计划。

## 原项目接线点

下列共享文件中的视频专属片段已从主项目删除，没有复制完整共享文件：

- `backend/app/__init__.py`：视频模型导入。
- `backend/app/papers/routes/__init__.py`：视频蓝图导入与注册。
- `backend/app/core/paths.py`：视频产物根目录和任务目录函数。
- `backend/app/core/llm/service.py`：`video_note` 模型调用场景。
- `frontend/src/app/router.tsx`、`route-components.tsx`、`AppShell.tsx`：路由、懒加载与导航。
- `frontend/src/api/types.ts`、`resources.ts`：视频任务类型和 API 封装。
- `frontend/src/index.css`：`.video-card` 与 `.video-transcript` 专属样式。
- `frontend/e2e/app.spec.ts`：视频 fixture、mock、路由和交互测试。

主项目的 Alembic 历史迁移仍保留原视频表演进记录。迁移 `a8d4e6f1b203` 从已有数据库删除对应空表。
