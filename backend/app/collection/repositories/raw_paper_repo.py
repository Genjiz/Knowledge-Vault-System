from app.collection.models import RawPaper
from app.core.extensions import db
from app.papers.repositories.base import BaseRepository


class RawPaperRepository(BaseRepository):
    model = RawPaper

    def replace_for_issue(self, raw_issue, papers):
        raw_issue.papers.clear()
        db.session.flush()

        created = []
        for index, paper in enumerate(papers):
            instance = RawPaper(
                raw_issue_id=raw_issue.id,
                source_identifier=paper.get("source_identifier"),
                title=paper["title"],
                title_zh=paper.get("title_zh"),
                authors=paper.get("authors"),
                abstract=paper.get("abstract"),
                abstract_zh=paper.get("abstract_zh"),
                keywords_json=paper.get("keywords_json"),
                pages=paper.get("pages"),
                detail_url=paper.get("detail_url"),
                published_at=paper.get("published_at"),
                sort_index=paper.get("sort_index", index),
                translation_status=paper.get("translation_status", "pending"),
            )
            db.session.add(instance)
            created.append(instance)

        db.session.commit()
        return created
