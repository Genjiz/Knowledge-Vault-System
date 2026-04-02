from app.models.base import BaseModel
from app.models.literature import Literature
from app.models.tag import Tag, LiteratureTag
from app.models.folder import Folder, LiteratureFolder
from app.models.note import Note

__all__ = [
    'BaseModel',
    'Literature',
    'Tag',
    'LiteratureTag',
    'Folder',
    'LiteratureFolder',
    'Note',
    'CrawlTask',
    'CrawlTaskLog',
    'LLMRun',
    'RawIssue',
    'RawIssueAnalysis',
    'RawPaper'
]


def __getattr__(name):
    if name in {'CrawlTask', 'CrawlTaskLog', 'LLMRun', 'RawIssue', 'RawIssueAnalysis', 'RawPaper'}:
        from app.crawler import models as crawler_models

        return getattr(crawler_models, name)
    raise AttributeError(f"module 'app.models' has no attribute {name!r}")
