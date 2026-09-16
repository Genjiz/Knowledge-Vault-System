# 代理与网络路由

本文说明 Windows 上不同代理机制的区别，以及 Knowledge Vault 当前每类网络请求采用的路由策略。

## 四类网络机制

1. **标准代理环境变量**：`HTTP_PROXY`、`HTTPS_PROXY`、`NO_PROXY`。Requests、HTTPX、curl 等支持这些变量的客户端可以读取它们。
2. **Windows 系统代理**：Windows 设置中的手动代理或自动配置脚本（PAC/WPAD）。Edge/Chromium 通常跟随该设置；Requests 在 Windows 上也可能通过 Python 的系统代理发现机制读取它，HTTPX 主要读取标准代理环境变量。
3. **显式客户端代理**：代码把代理 URL 直接传给某个 SDK 或 HTTP 客户端。此时代理来源唯一，不依赖客户端自动发现。
4. **网卡、TUN 或机构隧道**：Veee/Clash 的 TUN 模式、aTrust 等在更低网络层改变路由或出口。应用即使使用 `trust_env=False`，其“直连”流量仍会经过操作系统当前路由；`trust_env=False` 只是不读取应用层代理配置，不能绕过 TUN 或 aTrust。

本地 HTTP 代理地址通常形如 `http://127.0.0.1:<端口>`。访问 HTTPS 目标时，`HTTPS_PROXY` 的值仍常写成 `http://...`，客户端通过 HTTP CONNECT 建立隧道。端口由本机代理软件决定，例如当前 Veee 配置使用 `15236`，这不是其他机器的通用默认值。

## 标准变量

```env
HTTP_PROXY=http://127.0.0.1:15236
HTTPS_PROXY=http://127.0.0.1:15236
NO_PROXY=localhost,127.0.0.1,::1
```

- `HTTP_PROXY`：访问 HTTP 目标时使用的代理。
- `HTTPS_PROXY`：访问 HTTPS 目标时使用的代理。
- `NO_PROXY`：自动代理客户端应直连的主机列表，通常至少包含本机回环地址。
- 小写形式 `http_proxy`、`https_proxy`、`no_proxy` 也被很多工具支持；项目配置统一使用大写形式。

未配置时，这些环境变量不存在或为空。此时 Requests 在 Windows 上仍可能发现系统代理，浏览器也可能跟随系统代理；是否实际经过 TUN/aTrust 则由系统路由决定。

## `trust_env`

Requests 的 `Session.trust_env` 和 HTTPX 的同名选项控制客户端是否信任环境配置。

- `trust_env=True`：允许客户端自动读取其支持的代理环境。Requests 在 Windows 上还可能发现系统代理。
- `trust_env=False`：忽略这些自动发现的应用层代理。它不会删除环境变量，也不会关闭 Windows 系统代理、TUN、VPN 或 aTrust。

项目采用“默认请求使用标准环境，明确要求机构或国内出口的请求强制直连”的策略。强制直连的客户端创建专用 Session 并设置 `trust_env=False`；Gemini 则读取标准变量后显式传给 SDK，并关闭 SDK 的 `trust_env`，避免同一次请求再从其他来源发现代理。

## 当前行为矩阵

| 行为 | 实现与网络渠道 | 当前代理策略 |
|---|---|---|
| Gemini Native 模型调用 | Google GenAI SDK / HTTPX | 按 `HTTPS_PROXY` → `HTTP_PROXY`（再到对应小写变量）读取代理，显式传给 SDK，并设置 `trust_env=False`；未配置时不显式传代理 |
| OpenAI Compatible 模型调用 | OpenAI SDK / HTTPX | 未传自定义 HTTP 客户端，按 HTTPX 默认行为读取进程中的标准代理变量 |
| Scopus 题录与连接测试 | Requests Session | `trust_env=False`，应用层强制直连，以保留校园网或 aTrust 机构出口 |
| NCPSSD 题录、详情与连接测试 | 入口与 legacy 组件共享 Requests Session | `trust_env=False`，应用层强制直连；摘要接口不携带源码静态 Cookie |
| Magtech 题录、摘要与 PDF | Requests Session | 默认 Session 使用 `trust_env=False`，应用层强制直连 |
| Elsevier legacy 连接预检 | 模块级 Requests | 使用 Requests 默认自动代理行为 |
| Elsevier/ScienceDirect 浏览器采集与全文 | Edge/Chromium | Python 不设置浏览器代理，由 Windows、浏览器设置、扩展及 TUN/aTrust 决定 |
| 桌面启动器健康检查 | `urllib.request` | 显式使用空 `ProxyHandler`，确保 `localhost` / `127.0.0.1` 探测不经过应用层代理 |

`NO_PROXY` 只对会读取它的客户端生效。桌面健康检查仍保留空 `ProxyHandler`，因为启动器必须在 `.env` 尚未加载、父进程变量不规范或系统代理配置异常时也可靠检查本机服务。

## 配置加载边界

- 根目录 `.env` 是本机运行配置，不提交；`.env.example` 只提供变量结构。
- 后端由 Flask 运行时加载根目录 `.env`；Gemini 运行时也会显式查找并加载该文件。
- `python-dotenv` 使用 `override=False`：启动后端前已经存在的同名进程环境变量优先于 `.env`。
- `desktop.py` 不解析 `.env`，只复制自身环境并增加动态端口变量后启动子进程。
- Edge/Chromium 不读取项目 `.env`。
- `setup.ps1` 会在缺少时复制 `.env.example`，但不会先把 `.env` 导入安装命令的进程环境；pip/npm 安装是否走代理取决于启动 `setup.ps1` 时已有的环境和各工具配置。

修改 `.env` 后应重启托盘服务，使后端子进程重新加载配置。

## 常见运行场景

### 仅使用 Veee 本地 HTTP 代理

在 `.env` 填写 Veee 实际 HTTP 端口。Gemini、OpenAI Compatible 等可使用标准变量；Scopus、NCPSSD、Magtech 仍使用应用层直连。若 Veee 同时开启全局 TUN，后者是否最终经过 Veee 仍取决于 Veee 的路由规则，代码无法绕过 TUN。

### 校园网内

Scopus 直接使用当前校园网出口，无需配置额外应用代理。模型服务是否需要 Veee 取决于校园网是否能访问对应端点。

### 校外使用 aTrust

aTrust 通常通过隧道提供机构路由，不需要写入 `HTTP_PROXY`。Scopus 的应用层直连会沿系统路由使用 aTrust 出口；模型请求仍可通过 Veee 的标准代理变量处理。

### aTrust 与 Veee 同时开启

目标是机构服务走 aTrust，模型服务走 Veee。应用层已经把 Scopus/NCPSSD/Magtech 与模型请求分开；若 Veee 开启 TUN 或全局接管，还必须在 Veee 规则中把机构和国内域名设为直连，否则应用层 `trust_env=False` 也无法阻止 TUN 改写出口。

## 排查顺序

1. 确认目标请求属于上表哪一类，不要先假定所有网络请求共享同一配置。
2. 检查后端进程启动前是否已有同名代理变量；它们会覆盖 `.env`。
3. 检查 `.env` 中 URL、协议和端口是否与代理客户端当前监听端口一致，并重启服务。
4. 本地接口异常时确认 `NO_PROXY` 包含 `localhost,127.0.0.1,::1`；桌面健康检查本身已强制绕过代理。
5. 机构 API 返回 401/403 时检查校园网/aTrust 出口，不要把 Scopus 请求改走普通公网代理。
6. 强制直连仍出现代理出口时，检查 Windows 路由、Veee TUN/全局模式和 aTrust，而不是继续修改 `trust_env`。
7. 浏览器与 Python 表现不一致时，分别检查 Windows/浏览器代理和进程环境变量；两者不是同一配置层。
