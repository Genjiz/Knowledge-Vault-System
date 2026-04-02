# Documentation Map

这个文件是项目文档导航，也是 Agent 重启会话后最快的上下文入口。

## 建议阅读顺序

1. `README.md`
   作用：对外简介、快速启动、仓库定位
2. `docs/project-overview.md`
   作用：项目目标、当前范围、架构与目录
3. `docs/development-guide.md`
   作用：环境、启动、测试、配置、运行细节
4. `docs/roadmap.md`
   作用：产品方向与后续扩展重点
5. `docs/project-log.md`
   作用：重要变更、关键决策、阶段里程碑
6. `docs/plans/`
   作用：历史设计文档、实施计划、专题方案

## 各文档怎么更新

- `README.md`
  更新时机：对外定位、启动方式、核心能力发生变化时
- `docs/project-overview.md`
  更新时机：项目结构、架构边界、核心模块发生变化时
- `docs/development-guide.md`
  更新时机：环境要求、脚本、命令、配置方式发生变化时
- `docs/roadmap.md`
  更新时机：产品方向、阶段目标、优先级发生变化时
- `docs/project-log.md`
  更新时机：完成重要改造、做出关键决策、进入新阶段时
- `docs/plans/`
  更新时机：开始重要任务前新增方案文档，或补充历史设计说明时

## 当前真实结构

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

## 说明

- 仓库根目录就是项目根目录
- 旧的顶层说明文档已经拆分进 `docs/`
- 如果历史计划中出现旧目录结构，以本文件和 `docs/project-overview.md` 为准
