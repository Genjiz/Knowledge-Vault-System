"""端口分配工具。

端口决策集中在本模块，各入口只消费结果。前端代理目标、后端监听端口、启动器
打开的地址必须始终一致，分散写死会在端口冲突时各自漂移，产生「页面能开但接口全挂」
这类难以归因的故障。
"""
import socket

PROBE_HOST = "127.0.0.1"


def is_port_available(port: int, host: str = PROBE_HOST) -> bool:
    """检测端口当前是否可独占绑定。

    刻意不设置 SO_REUSEADDR：Windows 上该选项允许多个套接字绑定同一地址，
    会让正在监听的端口被误判为可用；不设置则行为保守，处于 TIME_WAIT 的端口
    也会被跳过，代价只是多顺延一个端口。
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
    except OSError:
        return False
    return True


def find_available_port(preferred: int, max_scan: int = 50) -> int:
    """从首选端口起返回第一个可绑定端口。

    首选端口空闲时直接返回，让多数情况下用户拿到的仍是熟悉的地址，只在冲突
    时才顺延。候选区间被占满时交给操作系统分配，避免无限扫描。
    """
    for port in range(preferred, preferred + max_scan):
        if is_port_available(port):
            return port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((PROBE_HOST, 0))
        return sock.getsockname()[1]
