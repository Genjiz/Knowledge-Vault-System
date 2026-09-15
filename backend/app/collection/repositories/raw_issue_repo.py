from app.collection.models import RawIssue
from app.papers.repositories.base import BaseRepository


class RawIssueRepository(BaseRepository):
    model = RawIssue

    def get_by_identity(self, source_type, journal_name, year, volume, issue):
        return self.model.query.filter_by(
            source_type=source_type,
            journal_name=journal_name,
            year=year,
            volume=volume,
            issue=issue,
        ).first()
