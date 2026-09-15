"""增加分析 Prompt 配置与全文文本资产

Revision ID: c4a8e6d2f713
Revises: b7e1d3f5a902
Create Date: 2026-09-10
"""

from alembic import op
import sqlalchemy as sa


revision = "c4a8e6d2f713"
down_revision = "b7e1d3f5a902"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "literature_text_asset",
        sa.Column("literature_id", sa.Integer(), nullable=True),
        sa.Column("source_pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("pipeline_version", sa.String(length=100), nullable=False),
        sa.Column("extractor_name", sa.String(length=100), nullable=True),
        sa.Column("extractor_version", sa.String(length=100), nullable=True),
        sa.Column("markdown_path", sa.String(length=1000), nullable=True),
        sa.Column("markdown_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts_json", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["literature_id"],
            ["literature.id"],
            name=op.f("fk_literature_text_asset_literature_id_literature"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_literature_text_asset")),
        sa.UniqueConstraint(
            "source_pdf_sha256",
            "pipeline_version",
            name="uq_text_asset_source_pipeline",
        ),
    )
    with op.batch_alter_table("literature_text_asset") as batch_op:
        batch_op.create_index(
            batch_op.f("ix_literature_text_asset_literature_id"),
            ["literature_id"],
            unique=False,
        )

    with op.batch_alter_table("paper_analysis") as batch_op:
        batch_op.add_column(
            sa.Column(
                "prompt_template_version",
                sa.String(length=100),
                nullable=False,
                server_default="paper-analysis-v1",
            )
        )
        batch_op.add_column(sa.Column("custom_instruction", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("include_fulltext", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("fulltext_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("fulltext_failed_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("fulltext_error_message", sa.Text(), nullable=True))

    with op.batch_alter_table("paper_analysis_item") as batch_op:
        batch_op.add_column(sa.Column("text_asset_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_paper_analysis_item_text_asset_id"),
            ["text_asset_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            batch_op.f(
                "fk_paper_analysis_item_text_asset_id_literature_text_asset"
            ),
            "literature_text_asset",
            ["text_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("paper_analysis_item") as batch_op:
        batch_op.drop_constraint(
            batch_op.f(
                "fk_paper_analysis_item_text_asset_id_literature_text_asset"
            ),
            type_="foreignkey",
        )
        batch_op.drop_index(batch_op.f("ix_paper_analysis_item_text_asset_id"))
        batch_op.drop_column("text_asset_id")

    with op.batch_alter_table("paper_analysis") as batch_op:
        batch_op.drop_column("fulltext_error_message")
        batch_op.drop_column("fulltext_failed_count")
        batch_op.drop_column("fulltext_count")
        batch_op.drop_column("include_fulltext")
        batch_op.drop_column("custom_instruction")
        batch_op.drop_column("prompt_template_version")

    with op.batch_alter_table("literature_text_asset") as batch_op:
        batch_op.drop_index(batch_op.f("ix_literature_text_asset_literature_id"))
    op.drop_table("literature_text_asset")
