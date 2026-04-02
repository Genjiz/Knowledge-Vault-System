from app.extensions import db
from app.models.base import BaseModel


class Tag(BaseModel):
    __tablename__ = 'tag'
    
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), default='#409EFF')
    
    literatures = db.relationship('Literature', secondary='literature_tag', back_populates='tags')
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'name': self.name,
            'color': self.color
        })
        return data


class LiteratureTag(db.Model):
    __tablename__ = 'literature_tag'
    
    literature_id = db.Column(db.Integer, db.ForeignKey('literature.id', ondelete='CASCADE'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
