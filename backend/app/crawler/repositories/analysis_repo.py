from app.crawler.models import RawIssueAnalysis
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository):
    model = RawIssueAnalysis
