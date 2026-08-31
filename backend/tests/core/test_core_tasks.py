import sys
import time
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.tasks import TaskExecutor


class TaskExecutorTestCase(unittest.TestCase):
    def test_submit_runs_function_in_background(self):
        executor = TaskExecutor()
        executed = []

        def work():
            executed.append("done")

        executor.submit("t1", work)
        time.sleep(0.2)

        self.assertEqual(executed, ["done"])

    def test_submit_returns_running_thread(self):
        executor = TaskExecutor()

        def work():
            time.sleep(0.3)

        thread = executor.submit("t2", work)

        self.assertTrue(thread.is_alive())
        self.assertTrue(executor.is_running("t2"))
        time.sleep(0.4)
        self.assertFalse(executor.is_running("t2"))

    def test_exception_invokes_on_error_callback(self):
        executor = TaskExecutor()
        errors = []

        def work():
            raise ValueError("boom")

        def on_error(exc):
            errors.append(exc)

        executor.submit("t3", work, on_error=on_error)
        time.sleep(0.2)

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(str(errors[0]), "boom")

    def test_exception_without_callback_does_not_crash(self):
        executor = TaskExecutor()

        def work():
            raise RuntimeError("silent")

        thread = executor.submit("t4", work)
        thread.join(timeout=2)

        self.assertFalse(thread.is_alive())

    def test_running_ids_lists_only_active_tasks(self):
        executor = TaskExecutor()

        def quick():
            pass

        def slow():
            time.sleep(0.3)

        executor.submit("quick", quick)
        executor.submit("slow", slow)
        time.sleep(0.1)

        self.assertIn("slow", executor.running_ids())
        self.assertNotIn("quick", executor.running_ids())
        time.sleep(0.3)


if __name__ == "__main__":
    unittest.main()
