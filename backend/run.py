import os
from app import create_app
from app.core.ports import find_available_port

app = create_app(os.environ.get('FLASK_ENV', 'development'))

DEFAULT_PORT = 5000


def resolve_port() -> int:
    """确定监听端口。

    启动器通过 KV_BACKEND_PORT 传入已确认可用的端口，此时端口再被占用属于
    环境异常，直接失败好过静默漂移；手工运行时没有该变量，才走自动顺延。
    """
    override = os.environ.get('KV_BACKEND_PORT')
    if override:
        return int(override)
    return find_available_port(DEFAULT_PORT)


def resolve_debug() -> bool:
    """默认关闭调试模式。

    调试模式的 reloader 会派生子进程并自行重启，与启动器的进程树生命周期
    管理相冲突；需要代码热重载时显式设置 FLASK_DEBUG=1。
    """
    return os.environ.get('FLASK_DEBUG', '0') not in ('0', '', 'false', 'False')


if __name__ == '__main__':
    port = resolve_port()
    print(f'[backend] listening on http://127.0.0.1:{port}', flush=True)
    app.run(host='0.0.0.0', port=port, debug=resolve_debug())
