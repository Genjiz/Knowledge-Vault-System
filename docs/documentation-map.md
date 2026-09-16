# Documentation Map

这个文件是项目文档导航，也是 Agent 重启会话后最快的上下文入口。文档职责的权威定义见根目录 `AGENTS.md` 第 6.1 节。

## 建议阅读顺序

1. `README.md`
   作用：对外简介、快速启动、仓库定位
2. `docs/current-architecture.md`
   作用：已实现并验证的当前架构、数据与产物位置、当前限制
3. `docs/proxy-and-network.md`
   作用：代理机制、当前请求分流、配置加载边界与排查方法
4. `docs/specifications/target-implementation-spec.md`
   作用：用户已确认的目标态（近期目标、中期方向、负面约束）
5. `docs/decisions/project-decisions.md`
   作用：长期有效的重要决策及理由
6. `docs/lessons/engineering-lessons.md`
   作用：已验证、可复用的工程经验
7. `docs/plans/`
   作用：设计与实施计划（`YYYY-MM-DD-<topic>.md`）

## 各文档怎么更新

- `README.md`
  更新时机：对外定位、启动方式、核心能力发生变化时
- `docs/current-architecture.md`
  更新时机：已实现的结构、数据流、路径规则、限制发生变化时；只写已验证事实
- `docs/proxy-and-network.md`
  更新时机：代理变量、客户端分流、浏览器或隧道路由策略发生变化时
- `docs/specifications/target-implementation-spec.md`
  更新时机：用户确认新的目标态或推翻既有目标态时
- `docs/decisions/project-decisions.md`
  更新时机：形成新的长期决策时（编号递增）
- `docs/lessons/engineering-lessons.md`
  更新时机：出现已验证、可能复用的工程经验时
- `docs/plans/`
  更新时机：开始复杂任务前新增计划文档，执行中同步更新进度

## 当前真实结构

```text
.
├─ backend/
├─ frontend/
├─ docs/
│  ├─ specifications/
│  ├─ decisions/
│  ├─ lessons/
│  ├─ plans/
│  └─ proxy-and-network.md
├─ desktop.py
├─ desktop.bat
├─ README.md
└─ AGENTS.md
```

## 说明

- 仓库根目录就是项目根目录
- 如果历史计划中出现旧目录结构或旧文档名，以本文件和 `AGENTS.md` 为准
