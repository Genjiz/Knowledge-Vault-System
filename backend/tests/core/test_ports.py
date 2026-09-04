import socket
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.ports import find_available_port, is_port_available


def occupy(port: int):
    """在回环地址上监听指定端口，用于模拟端口被占用。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)
    return sock


class PortToolsTestCase(unittest.TestCase):
    # 使用高位端口段，避免与本机实际服务或并行测试互相干扰
    BASE = 54310

    def test_free_port_is_reported_available(self):
        port = self.BASE + 1
        self.assertTrue(is_port_available(port))

    def test_listening_port_is_reported_unavailable(self):
        port = self.BASE + 2
        sock = occupy(port)
        try:
            self.assertFalse(is_port_available(port))
        finally:
            sock.close()

    def test_find_returns_preferred_port_when_free(self):
        port = self.BASE + 3
        self.assertEqual(find_available_port(port), port)

    def test_find_skips_occupied_port(self):
        occupied = self.BASE + 4
        expected = self.BASE + 5
        sock = occupy(occupied)
        try:
            self.assertEqual(find_available_port(occupied), expected)
        finally:
            sock.close()

    def test_find_falls_back_when_whole_range_occupied(self):
        start = self.BASE + 10
        socks = [occupy(p) for p in range(start, start + 5)]
        try:
            port = find_available_port(start, max_scan=5)
            # 候选区间占满时应交给系统分配，绝不返回被占用的端口
            self.assertNotIn(port, range(start, start + 5))
        finally:
            for sock in socks:
                sock.close()


if __name__ == "__main__":
    unittest.main()
