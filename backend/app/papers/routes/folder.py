from flask import Blueprint, request
from app.papers.repositories import folder_repo
from app.core import success_response, error_response

folder_bp = Blueprint('folder', __name__, url_prefix='/api/folders')


@folder_bp.route('', methods=['GET'])
def get_folders():
    tree = folder_repo.get_tree()
    return success_response(tree)


@folder_bp.route('/root', methods=['GET'])
def get_root_folders():
    folders = folder_repo.get_root_folders()
    return success_response([f.to_dict() for f in folders])


@folder_bp.route('/<int:folder_id>', methods=['GET'])
def get_folder(folder_id):
    folder = folder_repo.get_by_id(folder_id)
    if not folder:
        return error_response('文件夹不存在', 404)
    return success_response(folder.to_dict())


@folder_bp.route('/<int:folder_id>/children', methods=['GET'])
def get_children(folder_id):
    children = folder_repo.get_children(folder_id)
    return success_response([c.to_dict() for c in children])


@folder_bp.route('', methods=['POST'])
def create_folder():
    data = request.get_json()
    
    if not data.get('name'):
        return error_response('文件夹名称为必填项')
    
    folder = folder_repo.create(
        name=data['name'],
        parent_id=data.get('parent_id')
    )
    return success_response(folder.to_dict(), '文件夹创建成功')


@folder_bp.route('/<int:folder_id>', methods=['PUT'])
def update_folder(folder_id):
    folder = folder_repo.get_by_id(folder_id)
    if not folder:
        return error_response('文件夹不存在', 404)
    
    data = request.get_json()
    
    update_data = {}
    if 'name' in data:
        update_data['name'] = data['name']
    if 'parent_id' in data:
        if data['parent_id'] == folder_id:
            return error_response('不能将文件夹设为自己的子文件夹')
        update_data['parent_id'] = data['parent_id']
    
    folder_repo.update(folder_id, **update_data)
    folder = folder_repo.get_by_id(folder_id)
    return success_response(folder.to_dict(), '文件夹更新成功')


@folder_bp.route('/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folder = folder_repo.get_by_id(folder_id)
    if not folder:
        return error_response('文件夹不存在', 404)
    
    folder_repo.delete(folder_id)
    return success_response(message='文件夹删除成功')
