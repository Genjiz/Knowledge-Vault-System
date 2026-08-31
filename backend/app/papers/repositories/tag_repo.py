from app.papers.repositories.base import BaseRepository
from app.papers.models.tag import Tag
from app.core.extensions import db


class TagRepository(BaseRepository):
    model = Tag
    
    def get_by_name(self, name):
        return self.model.query.filter_by(name=name).first()
    
    def get_with_literature_count(self):
        from app.papers.models.tag import LiteratureTag
        from sqlalchemy import func
        
        result = db.session.query(
            Tag,
            func.count(LiteratureTag.literature_id).label('count')
        ).outerjoin(LiteratureTag).group_by(Tag.id).all()
        
        return [{'tag': tag.to_dict(), 'literature_count': count} for tag, count in result]
