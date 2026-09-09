# 代理与出网

出网有两类通道，作用不同。

## 两类通道

本地 HTTP 代理（Clash、V2Ray 及部分商业 VPN）在本机提供一个 HTTP 端口，地址形如 http://127.0.0.1:7890 或 http://127.0.0.1:15236，以当前客户端为准。只有程序把该地址当作代理使用时，请求才会经过它。访问 HTTPS 目标时，客户端仍填写 http 形式的本地代理 URL，由代理做 CONNECT 隧道。同一软件还可能另开 SOCKS 端口，HTTP 客户端走 HTTP 端口，SOCKS 客户端走 SOCKS 端口。

校园网隧道（如 aTrust）走系统网卡或 TUN，通常不提供本地 HTTP 端口。隧道开启后，进程里的直连对外已经是校园网 IP。环境变量 HTTP_PROXY 只影响会读取它的程序，不影响这类隧道。

机构订阅的学术 API（Scopus、ScienceDirect API 等）按出口 IP 判断权限。请求经过本地 HTTP 代理时，对方看到的是代理出口，订阅级字段会不可用。模型服务（Gemini、GPT 等）需要能访问其公网端点的出口，通常经过本地 HTTP 代理。

## 三层设置

代理可以出现在三层，彼此独立。

1. 操作系统的系统代理（Windows 设置 / WinINET）。浏览器常跟随这一层。Python 的 requests、httpx 默认不读系统代理。
2. 进程环境变量 HTTP_PROXY、HTTPS_PROXY、NO_PROXY。curl 以及 trust_env 为 True 的 Python 客户端读这一层。HTTPS 请求优先看 HTTPS_PROXY；NO_PROXY 列出直连的主机。python-dotenv 的 load_dotenv 会把 .env 写入环境变量，因此 .env 里的 HTTP_PROXY 会进入这一层。
3. 程序把代理 URL 传给具体客户端。由代码读取配置后显式传入。

直连或走代理由调用方在第 3 层决定。应用配置的变量名是 PROXY_URL。HTTP_PROXY、HTTPS_PROXY 留给会自动读环境变量的程序。

## trust_env

requests、httpx 的 trust_env 只控制是否读取第 2 层环境变量。

trust_env 为 True（不少库的默认值）时，客户端读取 HTTP_PROXY、HTTPS_PROXY、NO_PROXY。

trust_env 为 False 时，本次请求不读取这些环境变量。它不修改、不删除环境变量。

需要代理的客户端：传入代理 URL，trust_env 设为 False。
不需要代理的客户端：不传入代理，trust_env 设为 False。

直连与走代理都通过第 3 层的显式参数切换。启动器注入的 HTTP_PROXY 属于第 2 层，直连任务在第 3 层忽略它。

## 应用配置

本地 HTTP 代理地址写在配置里：

PROXY_URL=http://127.0.0.1:15236

值为完整 URL（协议、主机、端口）。需要出网代理的任务读取该值，传给对应客户端，trust_env 为 False。不需要代理的任务不读取该值，trust_env 为 False。

需要代理时，把 PROXY_URL 传给那个客户端。HTTP_PROXY、HTTPS_PROXY 保持原样，不在运行时改写成 PROXY_URL。

端口或客户端变化时，修改配置中的 URL，并重启使用该配置的进程。代理地址是本机网络入口，用配置文件维护。

## 按任务分流

| 任务 | 通道 |
|---|---|
| Scopus / ScienceDirect 等机构学术 API | 直连（校园网或校园隧道） |
| 国内站点与本地服务 | 直连 |
| Gemini、GPT 等国外模型 | PROXY_URL |
| 依赖机构 IP 或机构登录态的浏览器访问 | 系统网络；浏览器跟随系统代理，不另设本地 HTTP 代理 |
| 本地文件与数据库 | 不经过 HTTP 代理 |

校内时，学术 API 直连即可，出口已是校园网。校外时，先开校园隧道，再对学术 API 直连。

部分学术 API 还支持机构 Token，作为校园网 IP 之外的认证方式。直连解决出口身份，Token 解决账号授权。

## 校园隧道与本地 HTTP 代理同时开启

学术 API：校园隧道 + 直连。
模型请求：PROXY_URL 指向的本地 HTTP 代理。

学术 API 的域名走直连。本地代理若开启全局 TUN，对应规则为 DIRECT。

校园隧道与本地 HTTP 代理不是同一类配置。PROXY_URL 只填写确实提供了 HTTP 端口的软件地址。

## 核对出口

直连学术 API 时，出口是校园网地址。
走 PROXY_URL 时，出口是本地 HTTP 代理的出口。

两者不一致时，核对校园隧道是否开启、本地代理是否全局接管，以及该客户端是否传入了代理、trust_env 是否为 False。
