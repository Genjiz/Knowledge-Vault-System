import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.core.extensions import db


class PapersModelsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.ctx.pop()

    def test_journal_create_with_issn(self):
        from app.papers.models import Journal

        journal = Journal(name="情报学报", issn="1000-0135", publisher="中国科学技术情报学会")
        journal.save()

        fetched = db.session.get(Journal, journal.id)
        self.assertEqual(fetched.name, "情报学报")
        self.assertEqual(fetched.issn, "1000-0135")

    def test_journal_name_is_unique(self):
        from app.papers.models import Journal
        from sqlalchemy.exc import IntegrityError

        Journal(name="情报学报").save()
        with self.assertRaises(IntegrityError):
            Journal(name="情报学报").save()
        db.session.rollback()

    def test_journal_source_config_defaults(self):
        from app.papers.models import Journal, JournalSourceConfig

        journal = Journal(name="情报学报").save()
        config = JournalSourceConfig(journal_id=journal.id, source_id="ncpssd").save()

        fetched = db.session.get(JournalSourceConfig, config.id)
        self.assertEqual(fetched.source_id, "ncpssd")
        self.assertTrue(fetched.enabled)
        self.assertEqual(fetched.journal_id, journal.id)

    def test_literature_provenance_defaults(self):
        from app.papers.models import Literature

        paper = Literature(title="测试论文", authors="张三").save()

        fetched = db.session.get(Literature, paper.id)
        self.assertEqual(fetched.source, "imported")
        self.assertIsNone(fetched.journal_id)
        self.assertIsNone(fetched.source_raw_paper_id)

    def test_literature_can_link_journal_and_raw_paper(self):
        from app.papers.models import Journal, Literature

        journal = Journal(name="情报学报").save()
        paper = Literature(
            title="测试论文",
            authors="张三",
            journal_id=journal.id,
            source="collection",
            source_raw_paper_id=42,
        ).save()

        fetched = db.session.get(Literature, paper.id)
        self.assertEqual(fetched.journal_id, journal.id)
        self.assertEqual(fetched.source, "collection")
        self.assertEqual(fetched.source_raw_paper_id, 42)


if __name__ == "__main__":
    unittest.main()
