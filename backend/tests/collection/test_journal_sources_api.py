"""期刊与采集源 API 测试（T-1 阶段 3）。

源相关动作（测试连接、探测期号）走注入的 capability runner，
避免 papers 域反向依赖 collection 域。
"""
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class FakeRunner:
    """按 source_id 返回固定结果的假 runner，记录调用参数。"""

    def __init__(self, check_result=None, issues=None, error=None):
        self.check_result = check_result or {"status": "ok", "message": "已连通"}
        self.issues = issues if issues is not None else []
        self.error = error
        self.calls = []

    def test_connection(self, source_id, config, journal_name=None):
        self.calls.append(("test_connection", source_id, dict(config or {}), journal_name))
        if self.error:
            raise self.error
        return dict(self.check_result)

    def list_issues(self, source_id, config, year, journal_name=None):
        self.calls.append(("list_issues", source_id, dict(config or {}), year, journal_name))
        if self.error:
            raise self.error
        return list(self.issues)


class JournalSourcesApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.runner = FakeRunner()
        self.app.config["JOURNAL_SOURCE_RUNNER"] = self.runner

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def _create_journal(self, name="情报学报", **extra):
        response = self.client.post("/api/journals", json={"name": name, **extra})
        return response.get_json()["data"]["id"]

    def _unwrap(self, response):
        return response.get_json()["data"]


class SourceCatalogApiTestCase(JournalSourcesApiTestCase):
    def test_list_sources_returns_catalog(self):
        response = self.client.get("/api/collection/sources")

        self.assertEqual(response.status_code, 200)
        sources = {item["source_id"]: item for item in self._unwrap(response)}
        self.assertEqual(set(sources), {"ncpssd", "magtech", "elsevier"})
        self.assertTrue(sources["magtech"]["capabilities"]["list_issues"])
        self.assertEqual(
            sources["magtech"]["config_fields"][0]["key"], "base_url"
        )


class JournalCrudApiTestCase(JournalSourcesApiTestCase):
    def test_update_journal(self):
        journal_id = self._create_journal()

        response = self.client.put(
            f"/api/journals/{journal_id}",
            json={"issn": "1000-0135", "publisher": "中国科学技术信息研究所"},
        )

        self.assertEqual(response.status_code, 200)
        payload = self._unwrap(response)
        self.assertEqual(payload["issn"], "1000-0135")
        self.assertEqual(payload["publisher"], "中国科学技术信息研究所")

    def test_update_journal_rejects_duplicate_name(self):
        self._create_journal("情报学报")
        other_id = self._create_journal("现代情报")

        response = self.client.put(f"/api/journals/{other_id}", json={"name": "情报学报"})

        self.assertEqual(response.status_code, 409)

    def test_delete_journal(self):
        journal_id = self._create_journal()

        response = self.client.delete(f"/api/journals/{journal_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/journals").get_json()["data"], [])

    def test_delete_missing_journal_returns_404(self):
        self.assertEqual(self.client.delete("/api/journals/999").status_code, 404)


class JournalSourceConfigApiTestCase(JournalSourcesApiTestCase):
    def test_replace_sources_accepts_batch(self):
        journal_id = self._create_journal()

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={
                "sources": [
                    {
                        "source_id": "magtech",
                        "enabled": True,
                        "is_default": True,
                        "config": {"base_url": "https://qbxb.istic.ac.cn"},
                    },
                    {"source_id": "ncpssd", "enabled": True},
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        sources = {item["source_id"]: item for item in self._unwrap(response)["sources"]}
        self.assertEqual(set(sources), {"magtech", "ncpssd"})
        self.assertTrue(sources["magtech"]["is_default"])
        self.assertEqual(
            sources["magtech"]["config_json"], '{"base_url": "https://qbxb.istic.ac.cn"}'
        )

    def test_replace_sources_removes_omitted_sources(self):
        journal_id = self._create_journal()
        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "ncpssd", "enabled": True}]},
        )

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "magtech", "enabled": True, "config": {"base_url": "https://x.cn"}}]},
        )

        self.assertEqual(response.status_code, 200)
        sources = self._unwrap(response)["sources"]
        self.assertEqual([item["source_id"] for item in sources], ["magtech"])

    def test_replace_sources_keeps_single_default(self):
        """同一期刊至多一个默认源，后提交的生效。"""
        journal_id = self._create_journal()

        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={
                "sources": [
                    {"source_id": "ncpssd", "enabled": True, "is_default": True},
                    {"source_id": "magtech", "enabled": True, "is_default": True, "config": {"base_url": "https://x.cn"}},
                ]
            },
        )

        response = self.client.get("/api/journals")
        sources = self._unwrap(response)[0]["sources"]
        defaults = [item["source_id"] for item in sources if item["is_default"]]
        self.assertEqual(len(defaults), 1)

    def test_replace_sources_rejects_unknown_source(self):
        journal_id = self._create_journal()

        response = self.client.put(
            f"/api/journals/{journal_id}/sources", json={"sources": [{"source_id": "cnki", "enabled": True}]}
        )

        self.assertEqual(response.status_code, 400)

    def test_replace_sources_requires_config_of_enabled_source(self):
        """启用了需要 base_url 的源却没有填值时必须拦截。"""
        journal_id = self._create_journal()

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "magtech", "enabled": True}]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("base_url", response.get_json()["message"])

    def test_disabled_source_without_config_is_allowed(self):
        journal_id = self._create_journal()

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "magtech", "enabled": False}]},
        )

        self.assertEqual(response.status_code, 200)

    def test_replace_sources_rejects_region_mismatch(self):
        """国内期刊不允许启用国外源（如 elsevier），反之亦然。"""
        journal_id = self._create_journal()
        self.client.put(f"/api/journals/{journal_id}", json={"region": "domestic"})

        response = self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "elsevier", "enabled": True}]},
        )

        self.assertEqual(response.status_code, 400)


class SourceTestApiTestCase(JournalSourcesApiTestCase):
    def test_test_connection_persists_result(self):
        journal_id = self._create_journal()
        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "magtech", "enabled": True, "config": {"base_url": "https://qbxb.istic.ac.cn"}}]},
        )

        response = self.client.post(f"/api/journals/{journal_id}/sources/magtech/test")

        self.assertEqual(response.status_code, 200)
        payload = self._unwrap(response)
        self.assertEqual(payload["source_id"], "magtech")
        self.assertEqual(payload["last_check_status"], "ok")
        self.assertEqual(payload["last_check_message"], "已连通")
        self.assertIsNotNone(payload["last_checked_at"])

        # runner 收到的配置应来自 journal_source_config
        self.assertEqual(
            self.runner.calls[0][2], {"base_url": "https://qbxb.istic.ac.cn"}
        )

    def test_test_connection_unknown_source_returns_404(self):
        journal_id = self._create_journal()

        response = self.client.post(f"/api/journals/{journal_id}/sources/ncpssd/test")

        self.assertEqual(response.status_code, 404)

    def test_test_connection_failure_status_is_recorded(self):
        journal_id = self._create_journal()
        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "ncpssd", "enabled": True}]},
        )
        self.runner.error = RuntimeError("站点不可达")

        response = self.client.post(f"/api/journals/{journal_id}/sources/ncpssd/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._unwrap(response)["last_check_status"], "failed")
        self.assertIn("站点不可达", self._unwrap(response)["last_check_message"])


class IssueProbeApiTestCase(JournalSourcesApiTestCase):
    def test_probe_issues_returns_list(self):
        journal_id = self._create_journal()
        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "magtech", "enabled": True, "config": {"base_url": "https://x.cn"}}]},
        )
        self.runner.issues = [{"issue": "7", "volume": "45", "year": 2026}]

        response = self.client.get(
            f"/api/journals/{journal_id}/issues?source_id=magtech&year=2026"
        )

        self.assertEqual(response.status_code, 200)
        payload = self._unwrap(response)
        self.assertEqual(payload["issues"], [{"issue": "7", "volume": "45", "year": 2026}])
        self.assertEqual(payload["capabilities"]["list_issues"], True)

    def test_probe_issues_rejects_source_without_capability(self):
        journal_id = self._create_journal()
        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "ncpssd", "enabled": True}]},
        )

        response = self.client.get(f"/api/journals/{journal_id}/issues?source_id=ncpssd&year=2026")

        self.assertEqual(response.status_code, 400)

    def test_probe_issues_requires_year(self):
        journal_id = self._create_journal()

        response = self.client.get(f"/api/journals/{journal_id}/issues?source_id=magtech")

        self.assertEqual(response.status_code, 400)


class JournalListWithSourcesTestCase(JournalSourcesApiTestCase):
    def test_list_includes_sources_and_stats(self):
        from app.collection.models import CrawlTask, RawIssue

        journal_id = self._create_journal()
        self.client.put(
            f"/api/journals/{journal_id}/sources",
            json={"sources": [{"source_id": "ncpssd", "enabled": True, "is_default": True}]},
        )
        issue = RawIssue(
            source_type="ncpssd", region="domestic", journal_name="情报学报", year=2026, issue="3"
        )
        db.session.add(issue)
        db.session.commit()

        response = self.client.get("/api/journals")

        payload = self._unwrap(response)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["sources"][0]["source_id"], "ncpssd")
        self.assertEqual(payload[0]["stats"]["issue_count"], 1)
        self.assertIsNotNone(payload[0]["stats"]["last_collected_at"])


if __name__ == "__main__":
    unittest.main()
