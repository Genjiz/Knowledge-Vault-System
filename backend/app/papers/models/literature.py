from datetime import datetime
import json
from app.core.extensions import db
from app.papers.models.base import BaseModel


class Literature(BaseModel):
    __tablename__ = 'literature'
    
    title = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.Text, nullable=False)
    journal = db.Column(db.String(200))
    year = db.Column(db.Integer)
    volume = db.Column(db.String(20))
    issue = db.Column(db.String(20))
    pages = db.Column(db.String(50))
    doi = db.Column(db.String(100))
    abstract = db.Column(db.Text)
    keywords = db.Column(db.Text)
    pdf_path = db.Column(db.String(500))
    pdf_source_type = db.Column(db.String(50))
    pdf_source_raw_paper_id = db.Column(
        db.Integer,
        db.ForeignKey('raw_paper.id', ondelete='SET NULL'),
    )
    pdf_sha256 = db.Column(db.String(64))
    pdf_size_bytes = db.Column(db.BigInteger)
    url = db.Column(db.String(500))
    language = db.Column(db.String(20), default='en')
    literature_type = db.Column(db.String(20), default='journal')
    publisher = db.Column(db.String(200))
    status = db.Column(db.String(20), default='未读')
    status_changed_at = db.Column(db.DateTime)

    # 来源溯源：手动导入（imported）或采集入库（collection，关联 raw_paper）
    source = db.Column(db.String(20), nullable=False, default='imported', server_default='imported')
    source_raw_paper_id = db.Column(db.Integer)
    user_edited_fields_json = db.Column(db.Text)
    field_sources_json = db.Column(db.Text)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'))
    
    tags = db.relationship('Tag', secondary='literature_tag', back_populates='literatures')
    folders = db.relationship('Folder', secondary='literature_folder', back_populates='literatures')
    notes = db.relationship('Note', backref='literature', lazy='dynamic', cascade='all, delete-orphan')
    collection_sources = db.relationship(
        'LiteratureSource',
        back_populates='literature',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    fulltext_task_items = db.relationship(
        'FullTextTaskItem',
        back_populates='literature',
        lazy='selectin',
        passive_deletes=True,
    )
    
    def to_dict(self):
        try:
            field_sources = json.loads(self.field_sources_json or '{}')
        except (TypeError, ValueError):
            field_sources = {}
        data = super().to_dict()
        data.update({
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'year': self.year,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'doi': self.doi,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'pdf_path': self.pdf_path,
            'pdf_source_type': self.pdf_source_type,
            'pdf_source_raw_paper_id': self.pdf_source_raw_paper_id,
            'pdf_sha256': self.pdf_sha256,
            'pdf_size_bytes': self.pdf_size_bytes,
            'url': self.url,
            'language': self.language,
            'literature_type': self.literature_type,
            'publisher': self.publisher,
            'source': self.source,
            'source_raw_paper_id': self.source_raw_paper_id,
            'user_edited_fields_json': self.user_edited_fields_json,
            'field_sources': field_sources,
            'collection_sources': [source.to_dict() for source in self.collection_sources],
            'journal_id': self.journal_id,
            'status': self.status,
            'status_changed_at': self.status_changed_at.isoformat() if self.status_changed_at else None,
            'tags': [tag.to_dict() for tag in self.tags],
            'folder_ids': [folder.id for folder in self.folders]
        })
        return data
