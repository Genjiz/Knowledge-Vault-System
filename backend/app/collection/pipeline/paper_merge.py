"""采集原始论文与统一文献的多来源关联和字段物化。"""
import json

from app.collection.models import LiteratureSource
from app.collection.sources.registry import source_priority
from app.core.extensions import db
from app.core.text import clean_title_text
from app.papers.models import Literature
from app.papers.services.paper_service import (
    MATERIALIZED_FIELDS,
    PaperService,
    keywords_to_text,
    normalize_title,
    user_edited_fields,
)


_REGION_LANGUAGE = {"domestic": "zh", "foreign": "en"}
_SOURCE_REGION = {
    "ncpssd": "domestic",
    "magtech": "domestic",
    "elsevier": "foreign",
    "scopus": "foreign",
}
_MISSING_VOLUME_MARKERS = {"unknown"}
_MISSING_ISSUE_MARKERS = {"year", "unassigned"}


def _normalize_period_value(value, missing_markers):
    normalized = str(value or "").strip()
    if not normalized or normalized.casefold() in missing_markers:
        return None
    return normalized


def _resolve_language(raw_issue):
    region = (raw_issue.region or "").lower() or _SOURCE_REGION.get(
        (raw_issue.source_type or "").lower(), ""
    )
    return _REGION_LANGUAGE.get(region, "en")


class PaperMergeService:
    def __init__(self, paper_service=None):
        self.paper_service = paper_service or PaperService()

    def _paper_data(self, raw_paper):
        raw_issue = raw_paper.raw_issue
        volume = raw_paper.volume or raw_issue.volume
        issue = raw_paper.issue or raw_issue.issue
        return {
            "title": clean_title_text(raw_paper.title),
            "authors": raw_paper.authors or "",
            "journal": raw_issue.journal_name,
            "year": raw_issue.year,
            "volume": _normalize_period_value(volume, _MISSING_VOLUME_MARKERS),
            "issue": _normalize_period_value(issue, _MISSING_ISSUE_MARKERS),
            "abstract": raw_paper.abstract,
            "pages": raw_paper.pages,
            "doi": raw_paper.doi,
            "url": raw_paper.detail_url,
            "language": _resolve_language(raw_issue),
            "literature_type": "journal",
            "publisher": None,
            "keywords": keywords_to_text(raw_paper.keywords_json),
        }

    def _find_or_create_literature(self, raw_paper):
        existing_link = LiteratureSource.query.filter_by(raw_paper_id=raw_paper.id).first()
        if existing_link is not None:
            return existing_link.literature

        data = self._paper_data(raw_paper)
        literature = self._find_linked_match(data) or self.paper_service.find_collected_match(data)
        if literature is None:
            literature = Literature(
                title=data["title"],
                authors=data["authors"],
                source="collection",
                user_edited_fields_json="[]",
            )
            db.session.add(literature)
            db.session.flush()

        link = LiteratureSource(
            literature_id=literature.id,
            raw_paper_id=raw_paper.id,
            source_type=raw_paper.raw_issue.source_type,
        )
        db.session.add(link)
        db.session.flush()
        return literature

    def _find_linked_match(self, data):
        target_doi = str(data.get("doi") or "").strip().casefold()
        target_title = normalize_title(data.get("title"))
        for link in LiteratureSource.query.all():
            linked = self._paper_data(link.raw_paper)
            linked_doi = str(linked.get("doi") or "").strip().casefold()
            if target_doi and linked_doi == target_doi:
                return link.literature
            if not target_title or normalize_title(linked.get("title")) != target_title:
                continue
            if linked.get("journal") != data.get("journal"):
                continue
            if linked.get("year") != data.get("year"):
                continue
            if str(linked.get("issue") or "") != str(data.get("issue") or ""):
                continue
            return link.literature
        return None

    def recompute_literature(self, literature, commit=True):
        links = (
            LiteratureSource.query.filter_by(literature_id=literature.id)
            .order_by(LiteratureSource.id.desc())
            .all()
        )
        if not links:
            literature.source_raw_paper_id = None
            protected = user_edited_fields(literature)
            origins = {
                field: "user" if field in protected else "retained"
                for field in MATERIALIZED_FIELDS
                if getattr(literature, field, None) not in (None, "")
            }
            literature.field_sources_json = json.dumps(
                origins, ensure_ascii=False, sort_keys=True
            )
            if commit:
                db.session.commit()
            return literature

        links.sort(
            key=lambda link: (source_priority(link.source_type), link.raw_paper_id),
            reverse=True,
        )
        candidates = [(link, self._paper_data(link.raw_paper)) for link in links]
        protected = user_edited_fields(literature)
        origins = {field: "user" for field in protected}

        for field in MATERIALIZED_FIELDS:
            if field in protected:
                continue
            selected = next(
                (
                    (link.source_type, data[field])
                    for link, data in candidates
                    if data.get(field) not in (None, "")
                ),
                None,
            )
            if selected is not None:
                source_type, value = selected
                setattr(literature, field, value)
                origins[field] = source_type
            elif field not in ("title", "authors", "journal", "year"):
                setattr(literature, field, None)
                origins.pop(field, None)

        primary_link, primary_data = candidates[0]
        if literature.source != "imported":
            literature.source = "collection"
        literature.source_raw_paper_id = primary_link.raw_paper_id
        literature.field_sources_json = json.dumps(origins, ensure_ascii=False, sort_keys=True)
        if primary_data.get("journal") and "journal" not in protected:
            journal = self.paper_service.get_or_create_journal(primary_data["journal"])
            literature.journal_id = journal.id

        if commit:
            db.session.commit()
        return literature

    def upsert_raw_paper(self, raw_paper, commit=True):
        data = self._paper_data(raw_paper)
        if raw_paper.id is None:
            return self.paper_service.upsert_literature(data)
        literature = self._find_or_create_literature(raw_paper)
        return self.recompute_literature(literature, commit=commit)

    def unlink_issue(self, raw_issue):
        raw_paper_ids = [paper.id for paper in raw_issue.papers if paper.id is not None]
        if not raw_paper_ids:
            return set()
        links = LiteratureSource.query.filter(LiteratureSource.raw_paper_id.in_(raw_paper_ids)).all()
        affected = {link.literature_id for link in links}
        return affected

    def sync_issue(self, raw_issue, affected_literature_ids=None):
        literature_ids = set(affected_literature_ids or ())
        results = []
        for raw_paper in raw_issue.papers:
            literature = self.upsert_raw_paper(raw_paper, commit=False)
            literature_ids.add(literature.id)
            results.append(literature)

        for literature_id in literature_ids:
            literature = db.session.get(Literature, literature_id)
            if literature is not None:
                self.recompute_literature(literature, commit=False)
        db.session.commit()
        return results
