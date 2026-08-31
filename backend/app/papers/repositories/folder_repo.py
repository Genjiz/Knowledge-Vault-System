from app.papers.repositories.base import BaseRepository
from app.papers.models.folder import Folder
from app.core.extensions import db


class FolderRepository(BaseRepository):
    model = Folder
    
    def get_root_folders(self):
        return self.model.query.filter_by(parent_id=None).all()
    
    def get_children(self, parent_id):
        return self.model.query.filter_by(parent_id=parent_id).all()
    
    def get_tree(self):
        folders = self.model.query.all()
        return self._build_tree(folders, None)
    
    def _build_tree(self, folders, parent_id):
        tree = []
        for folder in folders:
            if folder.parent_id == parent_id:
                node = folder.to_dict()
                node['children'] = self._build_tree(folders, folder.id)
                tree.append(node)
        return tree
