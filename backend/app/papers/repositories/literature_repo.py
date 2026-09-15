from app.papers.repositories.base import BaseRepository
from app.papers.models.literature import Literature
from app.core.extensions import db


class LiteratureRepository(BaseRepository):
    model = Literature
    
    def search(self, keyword, page=1, per_page=10):
        search_pattern = f'%{keyword}%'
        query = self.model.query.filter(
            db.or_(
                self.model.title.ilike(search_pattern),
                self.model.authors.ilike(search_pattern),
                self.model.abstract.ilike(search_pattern),
                self.model.keywords.ilike(search_pattern)
            )
        )
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    def filter(self, page=1, per_page=10, status=None, language=None, year_start=None, year_end=None, tag_ids=None, folder_id=None, has_pdf=None, title=None, authors=None, abstract=None, journal_id=None, keyword=None):
        query = self.model.query

        if keyword:
            search_pattern = f'%{keyword}%'
            query = query.filter(
                db.or_(
                    self.model.title.ilike(search_pattern),
                    self.model.authors.ilike(search_pattern),
                    self.model.journal.ilike(search_pattern),
                    self.model.abstract.ilike(search_pattern),
                    self.model.keywords.ilike(search_pattern),
                )
            )
        
        if title:
            query = query.filter(self.model.title.ilike(f'%{title}%'))
        if authors:
            query = query.filter(self.model.authors.ilike(f'%{authors}%'))
        if abstract:
            query = query.filter(self.model.abstract.ilike(f'%{abstract}%'))
        if status:
            query = query.filter(self.model.status == status)
        if language:
            query = query.filter(self.model.language == language)
        if year_start:
            query = query.filter(self.model.year >= year_start)
        if year_end:
            query = query.filter(self.model.year <= year_end)
        if tag_ids:
            from app.papers.models.tag import LiteratureTag
            query = query.join(LiteratureTag).filter(LiteratureTag.tag_id.in_(tag_ids))
        if folder_id:
            from app.papers.models.folder import LiteratureFolder
            query = query.join(LiteratureFolder).filter(LiteratureFolder.folder_id == folder_id)
        if journal_id:
            query = query.filter(self.model.journal_id == journal_id)
        if has_pdf is not None:
            if has_pdf:
                query = query.filter(self.model.pdf_path.isnot(None))
            else:
                query = query.filter(self.model.pdf_path.is_(None))
        
        return query.order_by(self.model.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    def check_duplicate_doi(self, doi, exclude_id=None):
        if not doi:
            return None
        query = self.model.query.filter(self.model.doi == doi)
        if exclude_id:
            query = query.filter(self.model.id != exclude_id)
        return query.first()
    
    def get_statistics(self):
        from sqlalchemy import func
        from app.papers.models.tag import LiteratureTag
        
        total = self.model.query.count()
        
        status_stats = db.session.query(
            self.model.status,
            func.count(self.model.id)
        ).group_by(self.model.status).all()
        
        language_stats = db.session.query(
            self.model.language,
            func.count(self.model.id)
        ).group_by(self.model.language).all()
        
        monthly_stats = db.session.query(
            func.strftime('%Y-%m', self.model.created_at).label('month'),
            func.count(self.model.id)
        ).group_by('month').order_by('month').all()
        
        return {
            'total': total,
            'by_status': dict(status_stats),
            'by_language': dict(language_stats),
            'monthly': [{'month': m, 'count': c} for m, c in monthly_stats]
        }
