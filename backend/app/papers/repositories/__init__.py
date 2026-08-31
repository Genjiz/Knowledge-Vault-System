from app.papers.repositories.base import BaseRepository
from app.papers.repositories.literature_repo import LiteratureRepository
from app.papers.repositories.tag_repo import TagRepository
from app.papers.repositories.folder_repo import FolderRepository
from app.papers.repositories.note_repo import NoteRepository

literature_repo = LiteratureRepository()
tag_repo = TagRepository()
folder_repo = FolderRepository()
note_repo = NoteRepository()

__all__ = [
    'BaseRepository',
    'LiteratureRepository',
    'TagRepository',
    'FolderRepository',
    'NoteRepository',
    'literature_repo',
    'tag_repo',
    'folder_repo',
    'note_repo'
]
