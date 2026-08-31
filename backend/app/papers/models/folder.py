from app.core.extensions import db
from app.papers.models.base import BaseModel


class Folder(BaseModel):
    __tablename__ = 'folder'
    
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id', ondelete='CASCADE'))
    
    parent = db.relationship('Folder', remote_side='Folder.id', backref='children')
    literatures = db.relationship('Literature', secondary='literature_folder', back_populates='folders')
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'name': self.name,
            'parent_id': self.parent_id
        })
        return data


class LiteratureFolder(db.Model):
    __tablename__ = 'literature_folder'
    
    literature_id = db.Column(db.Integer, db.ForeignKey('literature.id', ondelete='CASCADE'), primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id', ondelete='CASCADE'), primary_key=True)
