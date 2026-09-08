"""多来源文献溯源、人工字段保护与标题清洗

Revision ID: d7b9e4a12f60
Revises: c4e2a9f81b37
Create Date: 2026-09-07 15:00:00.000000

"""
import html
import json
from html.parser import HTMLParser

from alembic import op
import sqlalchemy as sa


revision = "d7b9e4a12f60"
down_revision = "c4e2a9f81b37"
branch_labels = None
depends_on = None


_ALLOWED_TAGS = frozenset({"bold", "italic", "sup", "sub"})
_FIELDS = (
    "title",
    "authors",
    "journal",
    "year",
    "volume",
    "issue",
    "pages",
    "doi",
    "abstract",
    "keywords",
    "url",
    "language",
    "literature_type",
    "publisher",
)
_PRIORITIES = {"magtech": 300, "ncpssd": 200}


class _MarkupParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.stack = []
        self.valid = True

    def handle_starttag(self, tag, attrs):
        if tag not in _ALLOWED_TAGS:
            self.valid = False
            return
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag not in _ALLOWED_TAGS or not self.stack or self.stack[-1] != tag:
            self.valid = False
            return
        self.stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.valid = False

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(html.unescape(f"&{name};"))

    def handle_charref(self, name):
        self.parts.append(html.unescape(f"&#{name};"))

    def handle_comment(self, data):
        self.valid = False

    def handle_decl(self, decl):
        self.valid = False

    def unknown_decl(self, data):
        self.valid = False


def _clean_title(value):
    original = str(value or "")
    parser = _MarkupParser()
    try:
        parser.feed(original)
        parser.close()
    except (ValueError, AssertionError):
        return original.strip()
    if not parser.valid or parser.stack:
        return original.strip()
    return "".join(parser.parts).strip()


def _normalize_title(value):
    return " ".join(_clean_title(value).split()).casefold()


def _keywords_text(value):
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return value
    if isinstance(parsed, list):
        return ", ".join(str(item) for item in parsed)
    return value


def _row_data(row):
    region = (row.region or "").lower()
    if not region:
        region = "domestic" if row.source_type in ("ncpssd", "magtech") else "foreign"
    return {
        "title": _clean_title(row.title),
        "authors": row.authors or "",
        "journal": row.journal_name,
        "year": row.year,
        "volume": row.volume,
        "issue": row.issue,
        "pages": row.pages,
        "doi": row.doi,
        "abstract": row.abstract,
        "keywords": _keywords_text(row.keywords_json),
        "url": row.detail_url,
        "language": "zh" if region == "domestic" else "en",
        "literature_type": "journal",
        "publisher": None,
    }


def _protect_imported_fields(connection):
    rows = connection.execute(
        sa.text("SELECT * FROM literature WHERE source = 'imported'")
    ).mappings()
    for row in rows:
        protected = [field for field in _FIELDS if row.get(field) not in (None, "")]
        connection.execute(
            sa.text(
                "UPDATE literature SET user_edited_fields_json = :fields, "
                "field_sources_json = :origins WHERE id = :id"
            ),
            {
                "fields": json.dumps(protected, ensure_ascii=False),
                "origins": json.dumps({field: "user" for field in protected}, ensure_ascii=False),
                "id": row["id"],
            },
        )
    connection.execute(
        sa.text(
            "UPDATE literature SET user_edited_fields_json = '[]', field_sources_json = '{}' "
            "WHERE source = 'collection' AND user_edited_fields_json IS NULL"
        )
    )


def _clean_existing_titles(connection):
    raw_rows = connection.execute(
        sa.text("SELECT id, title, title_zh FROM raw_paper")
    ).mappings()
    for row in raw_rows:
        values = {
            "title": _clean_title(row["title"]),
            "title_zh": _clean_title(row["title_zh"]) if row["title_zh"] else row["title_zh"],
            "id": row["id"],
        }
        if values["title"] != row["title"] or values["title_zh"] != row["title_zh"]:
            connection.execute(
                sa.text(
                    "UPDATE raw_paper SET title = :title, title_zh = :title_zh WHERE id = :id"
                ),
                values,
            )

    rows = connection.execute(sa.text("SELECT id, title FROM literature")).mappings()
    for row in rows:
        cleaned = _clean_title(row["title"])
        if cleaned != row["title"]:
            connection.execute(
                sa.text("UPDATE literature SET title = :title WHERE id = :id"),
                {"title": cleaned, "id": row["id"]},
            )


def _load_raw_rows(connection):
    return list(
        connection.execute(
            sa.text(
                "SELECT rp.*, ri.source_type, ri.region, ri.journal_name, ri.year, "
                "ri.issue, ri.volume FROM raw_paper rp "
                "JOIN raw_issue ri ON ri.id = rp.raw_issue_id"
            )
        ).mappings()
    )


def _backfill_links(connection):
    raw_rows = _load_raw_rows(connection)
    raw_by_id = {row["id"]: row for row in raw_rows}
    literature_rows = list(
        connection.execute(sa.text("SELECT * FROM literature ORDER BY id")).mappings()
    )
    linked_raw_ids = set()

    def insert_link(literature_id, raw_row):
        if raw_row["id"] in linked_raw_ids:
            return
        connection.execute(
            sa.text(
                "INSERT INTO literature_source "
                "(literature_id, raw_paper_id, source_type, created_at, updated_at) "
                "VALUES (:literature_id, :raw_paper_id, :source_type, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "literature_id": literature_id,
                "raw_paper_id": raw_row["id"],
                "source_type": raw_row["source_type"],
            },
        )
        linked_raw_ids.add(raw_row["id"])

    for literature in literature_rows:
        raw_id = literature.get("source_raw_paper_id")
        if raw_id in raw_by_id:
            insert_link(literature["id"], raw_by_id[raw_id])

    for raw_row in raw_rows:
        if raw_row["id"] in linked_raw_ids:
            continue
        match = None
        raw_doi = str(raw_row.get("doi") or "").strip().casefold()
        if raw_doi:
            match = next(
                (
                    literature
                    for literature in literature_rows
                    if str(literature.get("doi") or "").strip().casefold() == raw_doi
                ),
                None,
            )
        if match is None:
            normalized = _normalize_title(raw_row["title"])
            match = next(
                (
                    literature
                    for literature in literature_rows
                    if literature.get("journal") == raw_row["journal_name"]
                    and literature.get("year") == raw_row["year"]
                    and str(literature.get("issue") or "") == str(raw_row["issue"])
                    and _normalize_title(literature.get("title")) == normalized
                ),
                None,
            )
        if match is not None:
            insert_link(match["id"], raw_row)


def _recompute_collection_literature(connection):
    literature_rows = list(
        connection.execute(
            sa.text("SELECT * FROM literature WHERE source = 'collection'")
        ).mappings()
    )
    journal_ids = {
        row["name"]: row["id"]
        for row in connection.execute(sa.text("SELECT id, name FROM journal")).mappings()
    }
    for literature in literature_rows:
        links = list(
            connection.execute(
                sa.text(
                    "SELECT rp.*, ri.source_type, ri.region, ri.journal_name, ri.year, "
                    "ri.issue, ri.volume FROM literature_source ls "
                    "JOIN raw_paper rp ON rp.id = ls.raw_paper_id "
                    "JOIN raw_issue ri ON ri.id = rp.raw_issue_id "
                    "WHERE ls.literature_id = :literature_id"
                ),
                {"literature_id": literature["id"]},
            ).mappings()
        )
        if not links:
            continue
        links.sort(
            key=lambda row: (_PRIORITIES.get(row["source_type"], 100), row["id"]),
            reverse=True,
        )
        candidates = [_row_data(row) for row in links]
        try:
            protected = set(json.loads(literature.get("user_edited_fields_json") or "[]"))
        except (TypeError, ValueError):
            protected = set()
        updates = {}
        origins = {field: "user" for field in protected}
        for field in _FIELDS:
            if field in protected:
                continue
            selected = next(
                (
                    (row["source_type"], data[field])
                    for row, data in zip(links, candidates)
                    if data.get(field) not in (None, "")
                ),
                None,
            )
            if selected is not None:
                source_type, value = selected
                updates[field] = value
                origins[field] = source_type
            elif field not in ("title", "authors", "journal", "year", "issue"):
                updates[field] = None
                origins.pop(field, None)
        updates["source_raw_paper_id"] = links[0]["id"]
        updates["field_sources_json"] = json.dumps(origins, ensure_ascii=False, sort_keys=True)
        journal_name = candidates[0].get("journal")
        if journal_name and "journal" not in protected:
            updates["journal_id"] = journal_ids.get(journal_name)
        assignments = ", ".join(f"{field} = :{field}" for field in updates)
        updates["id"] = literature["id"]
        connection.execute(
            sa.text(f"UPDATE literature SET {assignments} WHERE id = :id"), updates
        )


def upgrade():
    with op.batch_alter_table("literature", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_edited_fields_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("field_sources_json", sa.Text(), nullable=True))

    op.create_table(
        "literature_source",
        sa.Column("literature_id", sa.Integer(), nullable=False),
        sa.Column("raw_paper_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["literature_id"],
            ["literature.id"],
            name=op.f("fk_literature_source_literature_id_literature"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_paper_id"],
            ["raw_paper.id"],
            name=op.f("fk_literature_source_raw_paper_id_raw_paper"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_literature_source")),
        sa.UniqueConstraint("raw_paper_id", name="uq_literature_source_raw_paper"),
    )
    with op.batch_alter_table("literature_source", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_literature_source_literature_id"),
            ["literature_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_literature_source_raw_paper_id"),
            ["raw_paper_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_literature_source_source_type"),
            ["source_type"],
            unique=False,
        )

    connection = op.get_bind()
    _protect_imported_fields(connection)
    _clean_existing_titles(connection)
    _backfill_links(connection)
    _recompute_collection_literature(connection)


def downgrade():
    with op.batch_alter_table("literature_source", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_literature_source_source_type"))
        batch_op.drop_index(batch_op.f("ix_literature_source_raw_paper_id"))
        batch_op.drop_index(batch_op.f("ix_literature_source_literature_id"))
    op.drop_table("literature_source")

    with op.batch_alter_table("literature", schema=None) as batch_op:
        batch_op.drop_column("field_sources_json")
        batch_op.drop_column("user_edited_fields_json")
