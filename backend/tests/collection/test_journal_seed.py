"""内置期刊与源配置的播种测试（T-1 阶段 3）。

播种把「当前支持哪些期刊」从 legacy 缓存文件搬进数据库，只补不覆盖。
"""
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.collection.services.journal_seed import seed_known_journals
from app.core.extensions import db
from app.papers.models import Journal, JournalSourceConfig


class JournalSeedTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def _configs_of(self, name):
        journal = Journal.query.filter_by(name=name).first()
        return {row.source_id: row for row in journal.source_configs}

    def test_seed_creates_journals_from_ncpssd_cache(self):
        seed_known_journals()

        domestic_journals = ("情报学报", "现代情报", "图书情报知识", "情报理论与实践")
        for name in domestic_journals:
            journal = Journal.query.filter_by(name=name).first()
            self.assertIsNotNone(journal, name)
            self.assertEqual(journal.region, "domestic", name)
            self.assertTrue(self._configs_of(name)["ncpssd"].enabled, name)

    def test_seed_adds_elsevier_journal(self):
        """IP&M 是 Elsevier 源的首个示例期刊：区域国外，elsevier 为默认源。"""
        seed_known_journals()

        journal = Journal.query.filter_by(name="Information Processing & Management").first()
        self.assertIsNotNone(journal)
        self.assertEqual(journal.region, "foreign")
        configs = {row.source_id: row for row in journal.source_configs}
        self.assertIn("elsevier", configs)
        self.assertTrue(configs["elsevier"].enabled)
        self.assertTrue(configs["elsevier"].is_default)

    def test_seed_adds_magtech_source_with_base_url(self):
        seed_known_journals()

        magtech = self._configs_of("情报学报")["magtech"]
        self.assertTrue(magtech.enabled)
        self.assertIn("qbxb.istic.ac.cn", magtech.config_json)
        self.assertTrue(magtech.is_default)

    def test_seed_keeps_single_default(self):
        seed_known_journals()

        journal = Journal.query.filter_by(name="情报学报").first()
        defaults = [row for row in journal.source_configs if row.is_default]
        self.assertEqual(len(defaults), 1)

    def test_seed_is_idempotent(self):
        seed_known_journals()
        first_count = Journal.query.count()

        result = seed_known_journals()

        self.assertEqual(Journal.query.count(), first_count)
        self.assertEqual(result["created"], [])
        # 5 个期刊共 6 条源配置：4 个国内刊各 1 条 ncpssd + 情报学报 magtech + IP&M elsevier
        self.assertEqual(len(JournalSourceConfig.query.all()), 6)

    def test_seed_does_not_overwrite_existing_config(self):
        journal = Journal(name="情报学报")
        db.session.add(journal)
        db.session.flush()
        db.session.add(
            JournalSourceConfig(
                journal_id=journal.id,
                source_id="magtech",
                enabled=True,
                config_json='{"base_url": "https://custom.example.org"}',
            )
        )
        db.session.commit()

        seed_known_journals()

        self.assertEqual(
            self._configs_of("情报学报")["magtech"].config_json,
            '{"base_url": "https://custom.example.org"}',
        )

    def test_import_endpoint_seeds_and_returns_summary(self):
        response = self.client.post("/api/journals/import-known")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertIn("情报学报", payload["created"])
        self.assertGreaterEqual(self.client.get("/api/journals").get_json()["data"].__len__(), 4)


if __name__ == "__main__":
    unittest.main()
