from app.extensions import db


class BaseRepository:
    model = None
    
    def __init__(self):
        self.db = db
    
    def get_by_id(self, id):
        return db.session.get(self.model, id)
    
    def get_all(self):
        return self.model.query.all()
    
    def create(self, **kwargs):
        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    def update(self, id, **kwargs):
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            db.session.commit()
        return instance
    
    def delete(self, id):
        instance = self.get_by_id(id)
        if instance:
            db.session.delete(instance)
            db.session.commit()
        return instance
    
    def filter_by(self, **kwargs):
        return self.model.query.filter_by(**kwargs).all()
    
    def paginate(self, page=1, per_page=10, **kwargs):
        query = self.model.query
        for key, value in kwargs.items():
            if value is not None:
                query = query.filter_by(**{key: value})
        return query.paginate(page=page, per_page=per_page, error_out=False)
