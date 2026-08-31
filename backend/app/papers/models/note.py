from app.core.extensions import db
from app.papers.models.base import BaseModel


class Note(BaseModel):
    __tablename__ = 'note'
    
    literature_id = db.Column(db.Integer, db.ForeignKey('literature.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer)
    position_info = db.Column(db.String(200))
    excerpt_type = db.Column(db.String(50))
    rating = db.Column(db.Integer, default=0)
    action_required = db.Column(db.Text)
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'literature_id': self.literature_id,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'page_number': self.page_number,
            'position_info': self.position_info,
            'excerpt_type': self.excerpt_type,
            'rating': self.rating,
            'action_required': self.action_required
        })
        return data
