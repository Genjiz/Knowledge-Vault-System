"""统一 tag.name 唯一约束名称

Revision ID: b3f9c2a7d401
Revises: a8d4e6f1b203
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "b3f9c2a7d401"
down_revision = "a8d4e6f1b203"
branch_labels = None
depends_on = None


TARGET_CONSTRAINT_NAME = "uq_tag_name"
NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _tag_name_unique_constraints():
    return [
        constraint
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints("tag")
        if constraint["column_names"] == ["name"]
    ]


def upgrade():
    constraints = _tag_name_unique_constraints()
    if any(constraint["name"] == TARGET_CONSTRAINT_NAME for constraint in constraints):
        return

    if constraints:
        # SQLite 不能原地重命名约束；批量重建时命名约定会为旧的无名约束补名。
        with op.batch_alter_table(
            "tag",
            recreate="always",
            naming_convention=NAMING_CONVENTION,
        ):
            pass
        return

    with op.batch_alter_table("tag") as batch_op:
        batch_op.create_unique_constraint(TARGET_CONSTRAINT_NAME, ["name"])


def downgrade():
    # 无名约束无法被稳定引用，降级保留等价且已命名的唯一约束。
    pass
