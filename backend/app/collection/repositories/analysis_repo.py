from app.collection.models import RawIssueAnalysis
from app.papers.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository):
    model = RawIssueAnalysis
