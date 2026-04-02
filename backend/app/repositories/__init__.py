from app.repositories.base import BaseRepository
from app.repositories.literature_repo import LiteratureRepository
from app.repositories.tag_repo import TagRepository
from app.repositories.folder_repo import FolderRepository
from app.repositories.note_repo import NoteRepository

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
