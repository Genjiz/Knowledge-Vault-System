"""将 Scopus 年度批次拆分为卷期批次

Revision ID: b7e1d3f5a902
Revises: 9c2d7e4f1a60
Create Date: 2026-09-10
"""

from collections import OrderedDict

from alembic import op
import sqlalchemy as sa


revision = "b7e1d3f5a902"
down_revision = "9c2d7e4f1a60"
branch_labels = None
depends_on = None

UNKNOWN_VOLUME = "unknown"
UNASSIGNED_ISSUE = "unassigned"


def _split_scopus_year_rows(connection):
    metadata = sa.MetaData()
    raw_issue = sa.Table("raw_issue", metadata, autoload_with=connection)
    raw_paper = sa.Table("raw_paper", metadata, autoload_with=connection)
    rows = connection.execute(
        sa.select(raw_issue).where(
            raw_issue.c.source_type == "scopus",
            raw_issue.c.issue == "year",
        )
    ).mappings()

    for row in rows:
        papers = connection.execute(
            sa.select(raw_paper.c.id, raw_paper.c.volume, raw_paper.c.issue)
            .where(raw_paper.c.raw_issue_id == row["id"])
            .order_by(raw_paper.c.sort_index, raw_paper.c.id)
        ).mappings()
        groups = OrderedDict()
        for paper in papers:
            volume = str(paper["volume"] or "").strip() or UNKNOWN_VOLUME
            issue = str(paper["issue"] or "").strip() or UNASSIGNED_ISSUE
            groups.setdefault((volume, issue), []).append(paper["id"])
        if not groups:
            groups[(UNKNOWN_VOLUME, UNASSIGNED_ISSUE)] = []

        target_ids = []
        for index, ((volume, issue), paper_ids) in enumerate(groups.items()):
            values = dict(row)
            values.pop("id", None)
            values.update(
                volume=volume,
                issue=issue,
                paper_count=len(paper_ids),
                expected_paper_count=len(paper_ids),
                raw_json_path=None,
            )
            if index == 0:
                connection.execute(
                    raw_issue.update().where(raw_issue.c.id == row["id"]).values(**values)
                )
                target_id = row["id"]
            else:
                target_id = connection.execute(raw_issue.insert().values(**values)).inserted_primary_key[0]
            target_ids.append(target_id)
            if paper_ids:
                connection.execute(
                    raw_paper.update()
                    .where(raw_paper.c.id.in_(paper_ids))
                    .values(raw_issue_id=target_id)
                )


def upgrade():
    with op.batch_alter_table("raw_issue") as batch_op:
        batch_op.drop_constraint("uq_raw_issue_identity", type_="unique")

    connection = op.get_bind()
    _split_scopus_year_rows(connection)
    connection.execute(
        sa.text(
            "UPDATE raw_issue SET volume = :unknown "
            "WHERE volume IS NULL OR trim(volume) = ''"
        ),
        {"unknown": UNKNOWN_VOLUME},
    )

    with op.batch_alter_table("raw_issue") as batch_op:
        batch_op.create_unique_constraint(
            "uq_raw_issue_identity",
            ["source_type", "journal_name", "year", "volume", "issue"],
        )


def downgrade():
    with op.batch_alter_table("raw_issue") as batch_op:
        batch_op.drop_constraint("uq_raw_issue_identity", type_="unique")

    connection = op.get_bind()
    metadata = sa.MetaData()
    raw_issue = sa.Table("raw_issue", metadata, autoload_with=connection)
    raw_paper = sa.Table("raw_paper", metadata, autoload_with=connection)
    raw_analysis = sa.Table("raw_issue_analysis", metadata, autoload_with=connection)
    fulltext_task = sa.Table("fulltext_task", metadata, autoload_with=connection)

    identities = connection.execute(
        sa.select(
            raw_issue.c.journal_name,
            raw_issue.c.year,
        )
        .where(raw_issue.c.source_type == "scopus")
        .distinct()
    ).all()
    for journal_name, year in identities:
        condition = sa.and_(
            raw_issue.c.source_type == "scopus",
            raw_issue.c.journal_name == journal_name,
            raw_issue.c.year == year,
        )
        rows = connection.execute(sa.select(raw_issue).where(condition).order_by(raw_issue.c.id)).mappings().all()
        if not rows:
            continue
        target = rows[0]
        source_ids = [row["id"] for row in rows[1:]]
        if source_ids:
            connection.execute(
                raw_paper.update().where(raw_paper.c.raw_issue_id.in_(source_ids)).values(raw_issue_id=target["id"])
            )
            connection.execute(
                raw_analysis.update().where(raw_analysis.c.raw_issue_id.in_(source_ids)).values(raw_issue_id=target["id"])
            )
            connection.execute(
                fulltext_task.update().where(fulltext_task.c.raw_issue_id.in_(source_ids)).values(raw_issue_id=target["id"])
            )
            connection.execute(raw_issue.delete().where(raw_issue.c.id.in_(source_ids)))
        paper_count = connection.scalar(
            sa.select(sa.func.count()).select_from(raw_paper).where(raw_paper.c.raw_issue_id == target["id"])
        )
        connection.execute(
            raw_issue.update()
            .where(raw_issue.c.id == target["id"])
            .values(
                volume=None,
                issue="year",
                paper_count=paper_count,
                expected_paper_count=paper_count,
                raw_json_path=None,
            )
        )

    connection.execute(
        sa.text("UPDATE raw_issue SET volume = NULL WHERE volume = :unknown"),
        {"unknown": UNKNOWN_VOLUME},
    )
    with op.batch_alter_table("raw_issue") as batch_op:
        batch_op.create_unique_constraint(
            "uq_raw_issue_identity",
            ["source_type", "journal_name", "year", "issue"],
        )
