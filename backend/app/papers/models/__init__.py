from app.papers.models.base import BaseModel
from app.papers.models.literature import Literature
from app.papers.models.tag import Tag, LiteratureTag
from app.papers.models.folder import Folder, LiteratureFolder
from app.papers.models.journal import Journal, JournalSourceConfig
from app.papers.models.note import Note
from app.papers.models.paper_analysis import PaperAnalysis, PaperAnalysisItem

__all__ = [
    'BaseModel',
    'Literature',
    'Tag',
    'LiteratureTag',
    'Folder',
    'LiteratureFolder',
    'Note',
    'Journal',
    'JournalSourceConfig',
    'PaperAnalysis',
    'PaperAnalysisItem',
    'CrawlTask',
    'CrawlTaskLog',
    'LLMRun',
    'RawIssue',
    'RawIssueAnalysis',
    'RawPaper'
]


def __getattr__(name):
    if name in {'CrawlTask', 'CrawlTaskLog', 'LLMRun', 'RawIssue', 'RawIssueAnalysis', 'RawPaper'}:
        from app.collection import models as crawler_models

        return getattr(crawler_models, name)
    raise AttributeError(f"module 'app.papers.models' has no attribute {name!r}")
