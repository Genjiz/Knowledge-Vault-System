from app.crawler.models import RawIssue
from app.repositories.base import BaseRepository


class RawIssueRepository(BaseRepository):
    model = RawIssue

    def get_by_identity(self, source_type, journal_name, year, issue):
        return self.model.query.filter_by(
            source_type=source_type,
            journal_name=journal_name,
            year=year,
            issue=issue,
        ).first()
