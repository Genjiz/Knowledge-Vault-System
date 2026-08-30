# 2026-08-30 旧文档提炼迁移计划

## 1. 目标与范围

将 `docs/project-overview.md`、`docs/development-guide.md`、`docs/roadmap.md`、`docs/project-log.md` 四份旧文档的内容提炼迁移到新的文档体系中，然后删除这四个文件。迁移完成后，文档体系与新 `AGENTS.md` 第 6.1 节的清单一致。

## 2. 已确认决策与约束

- 新 `AGENTS.md` 已替换生效（2026-08-30），文档清单以其中第 6.1 节为准。
- 四份旧文档在内容提炼迁移后删除（用户已确认）。
- 写入可信度约束：`current-architecture.md` 只写已验证事实；`target-implementation-spec.md` 只写用户已确认的目标态；未确认的规划不迁移或明确标注状态。
- 时间流水不保留：`project-log.md` 中的条目只做提炼，流水本身不迁移。

## 3. 实施步骤

### 3.1 内容迁移映射

| 旧文档 | 内容 | 去向 |
|---|---|---|
| `project-overview.md` | 项目定位、能力清单 | 与 `README.md` 现有内容重复，不迁移（以 README 为准） |
| `project-overview.md` | 模块关系、数据流、当前限制（如有） | `docs/current-architecture.md`（仅限已验证事实） |
| `development-guide.md` | 环境搭建、启动关闭、常用命令 | `README.md`（README 已有大部分，缺的补入：运行测试命令、前后端单独启动命令） |
| `development-guide.md` | 视频转笔记模块运行要求 | `README.md` 模块说明段 |
| `development-guide.md` | 运行时路径细节（workspace 探测、legacy 位置、产物位置） | `docs/current-architecture.md` |
| `development-guide.md` | "文档维护要求"一节 | 不迁移（已由 `AGENTS.md` 第 6 节承接） |
| `roadmap.md` | 北极星定位、"从文献管理扩展到知识工作台"方向 | `docs/specifications/target-implementation-spec.md`（已确认方向） |
| `roadmap.md` | 近期重点中尚未与用户逐项确认的条目 | 不迁移；如需保留则明确标注"未确认" |
| `project-log.md` | 具有长期影响的决策（仓库扁平化、命名、采集先落原始数据再派生、video_notes 独立域等） | `docs/decisions/project-decisions.md`（编号 D-001 起，每条含状态/日期/内容/理由/影响） |
| `project-log.md` | 可复用工程经验（如有） | `docs/lessons/engineering-lessons.md` |
| `project-log.md` | 时间流水条目本身 | 不迁移 |

### 3.2 执行顺序

1. 创建 `docs/specifications/`、`docs/decisions/`、`docs/lessons/` 目录及三份初始文档；创建 `docs/current-architecture.md` 初版（内容取自四份旧文档中已验证的结构信息 + 当前代码结构核实结果）。
2. 按 3.1 映射完成内容提炼与写入。
3. 更新 `README.md`：文档入口链接指向新文档；补入缺失的命令与视频模块运行要求。
4. 更新 `docs/documentation-map.md`：按新文档清单重写导航。
5. 全仓检索四个旧文件名，确认无残留引用后删除四个旧文档。

### 3.3 验证

- `grep` 全仓（含代码、测试、文档）无对四个旧文档文件名的引用。
- 新文档间互相链接有效；`documentation-map.md` 与实际文件一一对应。
- `current-architecture.md` 中每条事实可对应到代码位置或运行验证结果。

## 4. 当前进度

- [x] 计划创建（2026-08-30）
- [x] 用户确认计划及三项遗留问题决策（2026-08-30：current-architecture 先写简版；roadmap 近期重点逐条确认后迁入；三个根目录辅助文件删除）
- [x] 步骤 3.2.1 创建四份新文档
- [x] 步骤 3.2.2 内容提炼与写入
- [x] 步骤 3.2.3 更新 README.md（文档入口、常用开发命令、视频模块运行要求）
- [x] 步骤 3.2.4 更新 documentation-map.md
- [x] 步骤 3.2.5 残留引用检查与旧文档删除

## 5. 计划偏差

- 无实质偏差。roadmap「近期重点 1/2/3」经用户逐条确认迁入 spec；「中期方向」与「暂不追求」经用户查看原文后确认迁入并标注性质。
- development-guide 引用的外部资料「B 站视频转笔记工作流.md」不在仓库内，无需迁移。
- 删除文件的命令输出出现 safe-delete 干扰性报错，经核实七个文件均已实际删除。

## 6. 验证结果

- 全仓检索旧文档文件名：代码与测试零引用；剩余引用仅位于历史 plans（属历史记录，documentation-map 已声明以新导航为准）、本文档与 project-decisions 的描述性文字。
- README.md、documentation-map.md、current-architecture.md、project-decisions.md 之间的链接均指向实际存在的新文档。
- docs/ 现存文件与 AGENTS.md 第 6.1 节清单一致。

## 7. 遗留问题

1. （已解决）current-architecture.md 以简版建立，完整版待后端架构重构后充实。
2. （已解决）roadmap 条目经逐条确认迁入 spec；近期重点 4「统一项目信息结构」由 AGENTS.md 第 6 节承接，不迁。
3. （已解决）三个根目录辅助文件（AGENTS_草案.md、AGENTS_参考.md、AGENTS_参考2.md）已删除。
