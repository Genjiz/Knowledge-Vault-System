from app.papers.repositories.base import BaseRepository
from app.papers.models.note import Note


class NoteRepository(BaseRepository):
    model = Note
    
    def get_by_literature(self, literature_id, note_type=None):
        query = self.model.query.filter_by(literature_id=literature_id)
        if note_type:
            query = query.filter_by(type=note_type)
        return query.order_by(self.model.created_at.desc()).all()
