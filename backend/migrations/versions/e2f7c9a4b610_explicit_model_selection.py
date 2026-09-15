"""显式选择模型并清理卷期内部标记

Revision ID: e2f7c9a4b610
Revises: d9f2a7c4e681
Create Date: 2026-09-10
"""

import json

from alembic import op
import sqlalchemy as sa


revision = "e2f7c9a4b610"
down_revision = "d9f2a7c4e681"
branch_labels = None
depends_on = None


def _normalize_literature_periods(connection):
    metadata = sa.MetaData()
    literature = sa.Table("literature", metadata, autoload_with=connection)
    rows = connection.execute(
        sa.select(
            literature.c.id,
            literature.c.volume,
            literature.c.issue,
            literature.c.user_edited_fields_json,
            literature.c.field_sources_json,
        )
    ).mappings()

    for row in rows:
        try:
            protected = set(json.loads(row["user_edited_fields_json"] or "[]"))
        except (TypeError, ValueError):
            protected = set()
        try:
            origins = json.loads(row["field_sources_json"] or "{}")
        except (TypeError, ValueError):
            origins = {}

        values = {}
        if (
            "volume" not in protected
            and str(row["volume"] or "").strip().casefold() == "unknown"
        ):
            values["volume"] = None
            origins.pop("volume", None)
        if (
            "issue" not in protected
            and str(row["issue"] or "").strip().casefold()
            in {"year", "unassigned"}
        ):
            values["issue"] = None
            origins.pop("issue", None)
        if values:
            values["field_sources_json"] = json.dumps(
                origins, ensure_ascii=False, sort_keys=True
            )
            connection.execute(
                literature.update()
                .where(literature.c.id == row["id"])
                .values(**values)
            )


def upgrade():
    with op.batch_alter_table("raw_issue") as batch_op:
        batch_op.add_column(sa.Column("translation_profile_id", sa.Integer()))
        batch_op.add_column(sa.Column("translation_model_name", sa.String(length=255)))
        batch_op.create_foreign_key(
            "fk_raw_issue_translation_profile_id_llm_profile",
            "llm_profile",
            ["translation_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("video_note_task") as batch_op:
        batch_op.add_column(sa.Column("profile_id", sa.Integer()))
        batch_op.add_column(sa.Column("model_name", sa.String(length=255)))
        batch_op.create_foreign_key(
            "fk_video_note_task_profile_id_llm_profile",
            "llm_profile",
            ["profile_id"],
            ["id"],
            ondelete="SET NULL",
        )

    _normalize_literature_periods(op.get_bind())
    op.drop_table("llm_scene_binding")


def downgrade():
    op.create_table(
        "llm_scene_binding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scene", sa.String(length=50), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["profile_id"], ["llm_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene"),
    )

    with op.batch_alter_table("video_note_task") as batch_op:
        batch_op.drop_constraint(
            "fk_video_note_task_profile_id_llm_profile", type_="foreignkey"
        )
        batch_op.drop_column("model_name")
        batch_op.drop_column("profile_id")

    with op.batch_alter_table("raw_issue") as batch_op:
        batch_op.drop_constraint(
            "fk_raw_issue_translation_profile_id_llm_profile", type_="foreignkey"
        )
        batch_op.drop_column("translation_model_name")
        batch_op.drop_column("translation_profile_id")
