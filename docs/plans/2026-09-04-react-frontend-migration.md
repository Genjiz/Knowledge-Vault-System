# React Frontend Migration Plan

## 1. 目标与范围

将 `frontend/` 从 Vue 3 + JavaScript 迁移为 React + TypeScript + Vite，在保持现有 Flask API、URL、主要用户行为、桌面启动器和端口编排不变的前提下，建立可持续扩展的前端工程基础。

目标技术栈：

- React + TypeScript + Vite
- Tailwind CSS 4 + shadcn/ui 风格的源码组件
- TanStack Router + TanStack Query
- React Hook Form + Zod
- Axios（迁移阶段保留现有 HTTP 语义）
- ECharts
- Vitest + React Testing Library
- Playwright 项目级 E2E
- ESLint + Prettier

本次不包含：

- Flask 后端架构重写；
- API URL 或响应格式的主动变更；
- Next.js、SSR、RSC 或 Node 业务服务端；
- TipTap 或新的富文本数据模型；
- 与迁移无关的产品功能扩张；
- 大规模视觉重设计。

## 2. 已确认决策与约束

- 用户已明确选择 React，不继续以 Vue 作为长期前端框架。
- 使用 React + TypeScript + Vite，不使用 Next.js。
- 继续使用 npm 和 `package-lock.json`，不引入 pnpm、Yarn 或其他锁文件。
- 保留独立 Flask HTTP API、SQLite、桌面托盘启动器和动态端口环境变量。
- 保持现有浏览器 URL，迁移期间以行为等价为第一优先级。
- 当前工作区已有大量业务改动；先验证并提交迁移前基线，不覆盖或丢失既有工作。
- 遵循 Red → Green → Refactor；跨框架迁移先建立关键行为基线。
- 新增代码注释使用中文。

## 3. 实施步骤

### P0 迁移前基线

1. 检查当前 Git 状态与现有计划进度。
2. 运行后端全量测试。
3. 运行当前 Vue 前端生产构建和 chunk 检查。
4. 修复阻断基线的问题，但不扩大既有业务范围。
5. 提交当前全部已验证改动作为迁移前检查点。
6. 创建并切换到 `codex/react-migration` 分支。

### P1 行为合同与测试基线

1. 盘点现有路由、API 模块、关键工作流、空态、错误态与文件操作。
2. 建立 Playwright E2E 基础设施。
3. 为可离线稳定执行的关键流程建立基线测试。
4. 对依赖正式数据或外部服务的流程使用 mock、临时数据或受控验证，不污染正式数据。

### P2 React 工程骨架

1. 更新依赖、脚本、TypeScript、Vite、ESLint、Prettier、Vitest 和 Tailwind 配置。
2. 建立 `app/`、`routes/`、`features/`、`components/`、`api/`、`config/`、`lib/` 目录边界。
3. 建立 TanStack Router、QueryClient、Axios Client、统一错误和通知机制。
4. 实现应用外壳、侧边栏、路由加载和通用 Loading/Empty/Error 状态。
5. 保留 `/api`、`/uploads` 代理与动态端口规则。

### P3 基础业务迁移

迁移仪表盘、标签、文件夹、统计、导入和备份。每个 Feature 先补纯逻辑或组件测试，再实现页面，并保持现有 API 与 URL。

### P4 文献工作台迁移

迁移文献列表、筛选、分页、详情、新增、编辑、删除、PDF 展示和笔记管理。普通笔记继续使用文本输入，不引入 TipTap。

### P5 采集中心迁移

迁移期刊与采集源、采集任务台、期号列表、期号详情和分析视图。长任务状态进入 TanStack Query，保留现有同步 API 的兼容行为，并为未来轮询预留 query 结构。

### P6 视频转笔记迁移

迁移视频任务创建、列表、详情、日志、字幕和 Markdown 下载。任务与日志使用 Query 管理，页面刷新后通过 URL 恢复。

### P7 清理与文档收尾

1. 删除 Vue、Pinia、Element Plus、Vue Router、Vue Quill 和 Vue ECharts 依赖及源码。
2. 确认只保留 `package-lock.json`。
3. 运行 lint、typecheck、unit/component test、E2E、build 和 chunk 检查。
4. 使用真实浏览器验证主要桌面流程、Console 和 Network。
5. 更新 README、当前架构、目标规范、项目决策和文档导航。
6. 核对 Git diff，不提交临时产物、日志或构建目录。

## 4. 当前进度

- [x] 用户确认目标技术栈和完整迁移授权。
- [x] 完成初步前端规模、路由、依赖和测试现状盘点。
- [ ] P0 迁移前基线（后端 155 项测试、Vue 构建与 chunk 检查已通过，待提交检查点并切分支）。
- [ ] P1 行为合同与测试基线。
- [ ] P2 React 工程骨架。
- [ ] P3 基础业务迁移。
- [ ] P4 文献工作台迁移。
- [ ] P5 采集中心迁移。
- [ ] P6 视频转笔记迁移。
- [ ] P7 清理与文档收尾。

## 5. 计划偏差

- 迁移前未提交旧 Vue 的 `frontend/node_modules`：该目录约 197 MiB，且将在 React 依赖安装时整体变化。最终提交迁移后的依赖快照，避免连续提交两份大体量依赖。

## 6. 验证结果

- 迁移前后端全量测试：155 项通过。
- 迁移前 Vue 生产构建：通过。
- 迁移前 chunk 检查：全部活动 JS chunk 小于 500 KB。

## 7. 遗留问题

- Flask 当前没有可复现的 OpenAPI Schema；迁移阶段先维护明确的 TypeScript API 合同，是否补齐后端 OpenAPI 作为独立后续任务评估。
- 当前项目规则仅声明 Node.js 18+；采用迁移时选定的 Vite 版本后，需要依据其实际 `engines` 要求更新环境说明。
