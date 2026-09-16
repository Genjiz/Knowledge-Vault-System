"""移除视频笔记任务表

Revision ID: a8d4e6f1b203
Revises: f6b8c1d3e742
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "a8d4e6f1b203"
down_revision = "f6b8c1d3e742"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("video_note_task_log")
    op.drop_table("video_note_task")


def downgrade():
    op.create_table(
        "video_note_task",
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("bvid", sa.String(length=64), nullable=False),
        sa.Column("video_title", sa.String(length=500)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=64)),
        sa.Column("progress_message", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("whisper_model", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("device", sa.String(length=32), nullable=False),
        sa.Column("compute_type", sa.String(length=32), nullable=False),
        sa.Column("use_vad", sa.Boolean(), nullable=False),
        sa.Column("profile_id", sa.Integer()),
        sa.Column("model_name", sa.String(length=255)),
        sa.Column("audio_path", sa.Text()),
        sa.Column("transcript_path", sa.Text()),
        sa.Column("note_path", sa.Text()),
        sa.Column("metadata_path", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["llm_profile.id"],
            name="fk_video_note_task_profile_id_llm_profile",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_note_task_bvid", "video_note_task", ["bvid"])
    op.create_table(
        "video_note_task_log",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["task_id"], ["video_note_task.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_video_note_task_log_task_id",
        "video_note_task_log",
        ["task_id"],
    )
