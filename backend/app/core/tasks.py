"""统一后台任务执行器（PE）。

线程包装 + 状态跟踪 + 异常回调。执行器不感知具体业务域：
任务的状态落库与日志由调用方通过 on_error 等回调完成。
"""
import threading


class TaskExecutor:
    """基于 daemon 线程的任务执行器。

    - submit(task_id, fn, on_error=None)：后台运行 fn，异常经 on_error(exc) 回调；
    - is_running(task_id) / running_ids()：查询在跑任务；
    - 同一 task_id 重复 submit 会替换记录，不阻止并发（调用方负责幂等）。
    """

    def __init__(self):
        self._threads = {}
        self._lock = threading.Lock()

    def submit(self, task_id, fn, on_error=None):
        def _run():
            try:
                fn()
            except Exception as exc:
                if on_error is not None:
                    try:
                        on_error(exc)
                    except Exception:
                        pass

        thread = threading.Thread(target=_run, name=f"task-{task_id}", daemon=True)
        with self._lock:
            self._threads[task_id] = thread
        thread.start()
        return thread

    def is_running(self, task_id):
        with self._lock:
            thread = self._threads.get(task_id)
        return thread is not None and thread.is_alive()

    def running_ids(self):
        with self._lock:
            return [tid for tid, thread in self._threads.items() if thread.is_alive()]
