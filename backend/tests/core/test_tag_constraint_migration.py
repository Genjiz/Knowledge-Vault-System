import importlib
import unittest

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_MODULE = "migrations.versions.b3f9c2a7d401_name_tag_unique_constraint"


class TagConstraintMigrationTestCase(unittest.TestCase):
    def setUp(self):
        self.migration = importlib.import_module(MIGRATION_MODULE)

    def _create_database(self, constraint_name):
        engine = sa.create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        metadata = sa.MetaData()
        tag = sa.Table(
            "tag",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("color", sa.String(length=7)),
            sa.UniqueConstraint("name", name=constraint_name),
        )
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                tag.insert(),
                [{"name": "重点", "color": "#409EFF"}],
            )
        return engine

    def _upgrade(self, engine):
        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                self.migration.upgrade()

    def _assert_named_unique_constraint(self, engine):
        constraints = sa.inspect(engine).get_unique_constraints("tag")
        self.assertEqual(
            constraints,
            [{"name": "uq_tag_name", "column_names": ["name"]}],
        )

        with engine.connect() as connection:
            rows = connection.execute(
                sa.text("SELECT name, color FROM tag ORDER BY id")
            ).all()
        self.assertEqual(rows, [("重点", "#409EFF")])

        with self.assertRaises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "INSERT INTO tag (name, color) VALUES (:name, :color)"
                    ),
                    {"name": "重点", "color": "#FFFFFF"},
                )

    def test_upgrade_names_existing_unnamed_unique_constraint(self):
        engine = self._create_database(constraint_name=None)

        self._upgrade(engine)

        self._assert_named_unique_constraint(engine)

    def test_upgrade_is_noop_when_constraint_is_already_named(self):
        engine = self._create_database(constraint_name="uq_tag_name")

        self._upgrade(engine)

        self._assert_named_unique_constraint(engine)


if __name__ == "__main__":
    unittest.main()
