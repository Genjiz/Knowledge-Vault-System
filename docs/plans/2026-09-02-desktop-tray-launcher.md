# 桌面托盘启动器与端口管理改造

## 1. 目标与范围

把项目的启动方式从「双击 bat 弹出三个常驻终端窗口」改为「双击图标启动、托盘常驻、右键退出」，同时消除端口写死带来的启动失败隐患。

**纳入范围**

- 根目录新增 `desktop.py`：托盘启动器，统一编排前后端进程的生命周期
- 端口管理：后端与前端端口可配置、被占用时自动顺延、实际端口落盘
- 依赖新增：`pystray`、`Pillow`
- 文档同步：README、current-architecture、decisions、lessons、.gitignore

**不纳入范围**

- 不引入 Tauri / Electron / pywebview 等桌面框架（用户明确不需要独立窗口）
- 不改动任何业务代码（Flask 路由、前端页面、数据模型均不动）
- 不改动 `start.bat` / `stop.bat` 的原有行为，保留为无依赖备用入口
- 不做安装包分发

## 2. 已确认决策与约束

| 编号 | 决策 | 理由 |
|---|---|---|
| 1 | 保留 HTTP 通信，不追求「零端口」 | 零端口需将整套 Flask 路由重写为函数绑定（pywebview expose / Tauri command），成本远高于收益 |
| 2 | 端口编排权交给启动器，前后端只消费 | 单一决策点，避免三处各自写死后互相错位 |
| 3 | 端口策略为「首选 + 自动顺延」，而非 `port=0` 随机分配 | 用户多数情况下仍能拿到熟悉的 5000/3000，地址可预测 |
| 4 | 健康检查用轮询 `/api/health`，替换 `timeout /t 2` | 后端启动耗时不确定，固定等待不可靠 |
| 5 | 退出时按进程树 kill，而非按端口 kill | 端口可能已被顺延，按端口杀会漏掉或误杀 |
| 6 | 托盘图标由 Pillow 运行时生成，不引入图片资源文件 | 减少资源文件维护，避免路径问题 |
| 7 | 沿用项目约定：Python 用 `.venv`，依赖写入 `backend/requirements.txt` | AGENTS.md 第 4 节 |

## 3. 实施步骤

### 步骤 1：端口公共设施

新增 `backend/app/core/ports.py`，提供 `find_available_port(preferred, max_scan)`：
从首选端口起逐个尝试绑定 `127.0.0.1`，返回第一个可绑定端口；全部失败时退回 `port=0` 由系统分配。

### 步骤 2：后端入口改造

`backend/run.py`：

- 读取环境变量 `KV_BACKEND_PORT`
- 显式指定 → 直接使用，被占用则报错退出（明确失败，不静默漂移）
- 未指定 → 从 5000 起自动顺延，并在日志打印实际端口
- 关闭 `debug=True`（Flask reloader 会 fork 子进程，导致启动器无法按进程树回收）

### 步骤 3：前端配置改造

`frontend/vite.config.js`：

- 代理目标改读 `process.env.KV_BACKEND_PORT`，默认 5000
- 服务端口改读 `process.env.KV_FRONTEND_PORT`，默认 3000
- 仅当启动器注入了 `KV_FRONTEND_PORT` 时启用 `strictPort`，保证端口确定；手工 `npm run dev` 时保留 Vite 默认顺延行为

### 步骤 4：托盘启动器

根目录 `desktop.py`：

1. 单实例检测：读 `.runtime/ports.json`，若后端 health 已通过则直接打开界面并退出
2. 分配前后端端口，写入 `.runtime/ports.json`
3. 以无窗口方式（`CREATE_NO_WINDOW`）拉起 `python run.py` 与 `npm run dev`，stdout/stderr 落盘到 `.runtime/logs/`
4. 轮询 `/api/health` 直到就绪或超时（超时则提示并保留日志路径）
5. 用 Edge `--app=<url>` 模式打开界面（探测不到 Edge 时退回系统默认浏览器）
6. 托盘图标常驻，右键菜单：打开界面 / 重启服务 / 退出
7. 退出时按进程树 kill（`taskkill /f /t /pid`），清理 `.runtime/ports.json`

### 步骤 5：依赖与验证

- `.venv` 安装 `pystray`、`Pillow`（`--no-cache-dir`，见 lessons L-001）
- 写入 `backend/requirements.txt`
- 端到端验证：端口顺延、健康检查、启动、界面可访问、退出后无残留进程
- 跑后端相关测试；前端 `npm run build` 验证配置改动未破坏构建（清空 `NODE_OPTIONS`，见 lessons L-006）

### 步骤 6：文档同步

按 AGENTS.md 6.4 更新受影响文档。

## 4. 当前进度

- [x] 计划文档编写
- [x] 步骤 1 端口公共设施（`backend/app/core/ports.py` + 单元测试 5 个）
- [x] 步骤 2 后端入口改造（`KV_BACKEND_PORT`、自动顺延、默认关闭 reloader）
- [x] 步骤 3 前端配置改造（环境变量端口、`host: 127.0.0.1`、条件 `strictPort`）
- [x] 步骤 4 托盘启动器（`desktop.py` + `desktop.bat`）
- [x] 步骤 5 依赖与验证
- [x] 步骤 6 文档同步

## 5. 计划偏差

- 原计划直接用 `127.0.0.1` 探测前端，实测失败。原因有两个独立来源：Vite 5 未显式指定 host 时按 `localhost` 监听，Node 17+ 可能优先解析为 IPv6，实际只绑定 `[::1]`；系统代理会把回环请求转发后返回 502。修正为：Vite 配置显式 `host: '127.0.0.1'`，探测代码统一禁用代理（经验沉淀为 lessons L-007、L-008）。
- 原计划未包含端口模块单元测试与 `desktop.bat`，实施中补充：TDD 要求为 `ports.py` 配套 `backend/tests/core/test_ports.py`；`desktop.bat` 作为用户双击入口（自动安装缺失依赖，经 pythonw 无窗口启动）。
- 后端 `debug=True` 改为默认关闭（reloader 子进程与进程树回收冲突），属可感知行为变更，已写入决策记录 D-014。

## 6. 验证结果

- 单元测试：`backend/tests/core/test_ports.py` 5 个用例通过（空闲判定、占用判定、首选命中、顺延、区间占满回退）。
- 后端全量套件：102 个测试通过（`unittest discover`，退出码 0）。
- 前端构建：`npm run build` 成功（按 L-006 清空 `NODE_OPTIONS` 并预清 dist）。
- 端到端（启动器 `Services` 类，真实拉起前后端）：分配 5000/3000 → 后端 health 200 → 前端页面就绪 → 经 Vite 代理访问 `/api/health` 返回 code 200 → `.runtime/ports.json` 生成 → `stop()` 后端口文件删除、前后端端口无残留监听。
- 端口顺延实测：占用 5000 后启动后端，实际监听 5001。
- 显式端口实测：`KV_BACKEND_PORT=5021` 时后端监听 5021，health 通过。
- 沙箱内无法验证托盘 UI 的视觉与交互（需真实桌面会话），`icon.run()` 托盘部分待用户双击 `desktop.bat` 实测。

## 7. 遗留问题

- 托盘图标显示、右键菜单、Edge 应用模式窗口需用户实际运行 `desktop.bat` 确认体验；若 Edge 探测路径不符可再调整。
- `stop.bat` 仍按固定 3000/5000 kill，端口被顺延的场景下兜底不完全；托盘「退出」是可靠的停止方式，`stop.bat` 仅作应急。
- `desktop.bat` 首次运行会自动 `pip install` 依赖，依赖安装失败时仅写入 `.runtime/logs/launcher.log`，无界面提示。

## 8. 修复轮次（2026-09-03）

用户实测反馈：托盘图标不出现；不要 Edge 应用模式窗口，用传统浏览器页面即可。

- **托盘图标不出现的根因**：`Icon.run(setup=...)` 传入自定义 setup 后，pystray 默认 setup（`icon.visible = True`）不再执行，图标注册了却永远不可见；pythonw 下静默无感知。修复：自定义 setup 中显式 `icon.visible = True`（沉淀为 lessons L-009）。
- **连带修复**：pystray MenuItem 的 action 以 `(icon, item)` 两参数被调用，原无参 lambda 会在点击菜单时报错，已统一改为双参数；`__main__` 增加全局异常兜底写日志，pythonw 下失败不再不可排查。
- **按用户要求移除 Edge 应用模式**：`open_in_browser()` 改用 `webbrowser.open`（系统默认浏览器），Edge 探测常量删除。
- **清理孤儿进程**：修复前实测确认服务在后台运行而托盘不可见，用户无法退出；已手动清理 5000/3000 监听进程与挂起的 pythonw。
- 关于「关闭窗口即关闭服务」的备选：改用传统浏览器后浏览器页面不属于应用，关页面即停服务不成立，托盘退出是唯一可靠停止入口，此备选不再需要。
- 修复后验证：托盘冒烟测试（setup 后 `icon.visible is True`）通过；托盘 + 服务完整流程端到端通过（5000/3000 就绪、浏览器打开调用一次、退出无残留）。
