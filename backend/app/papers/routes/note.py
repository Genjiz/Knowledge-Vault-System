from flask import Blueprint, request
from app.papers.repositories import note_repo, literature_repo
from app.core import success_response, error_response

note_bp = Blueprint('note', __name__, url_prefix='/api/notes')


@note_bp.route('', methods=['GET'])
def get_notes():
    literature_id = request.args.get('literature_id', type=int)
    note_type = request.args.get('type')
    
    if not literature_id:
        return error_response('文献ID为必填项')
    
    literature = literature_repo.get_by_id(literature_id)
    if not literature:
        return error_response('文献不存在', 404)
    
    notes = note_repo.get_by_literature(literature_id, note_type)
    return success_response([n.to_dict() for n in notes])


@note_bp.route('/<int:note_id>', methods=['GET'])
def get_note(note_id):
    note = note_repo.get_by_id(note_id)
    if not note:
        return error_response('笔记不存在', 404)
    return success_response(note.to_dict())


@note_bp.route('', methods=['POST'])
def create_note():
    data = request.get_json()
    
    if not data.get('literature_id'):
        return error_response('文献ID为必填项')
    if not data.get('type'):
        return error_response('笔记类型为必填项')
    if not data.get('content'):
        return error_response('笔记内容为必填项')
    
    literature = literature_repo.get_by_id(data['literature_id'])
    if not literature:
        return error_response('文献不存在', 404)
    
    note = note_repo.create(
        literature_id=data['literature_id'],
        type=data['type'],
        title=data.get('title'),
        content=data['content'],
        page_number=data.get('page_number'),
        position_info=data.get('position_info'),
        excerpt_type=data.get('excerpt_type'),
        rating=data.get('rating', 0),
        action_required=data.get('action_required')
    )
    return success_response(note.to_dict(), '笔记创建成功')


@note_bp.route('/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    note = note_repo.get_by_id(note_id)
    if not note:
        return error_response('笔记不存在', 404)
    
    data = request.get_json()
    
    update_data = {}
    if 'type' in data:
        update_data['type'] = data['type']
    if 'title' in data:
        update_data['title'] = data['title']
    if 'content' in data:
        update_data['content'] = data['content']
    if 'page_number' in data:
        update_data['page_number'] = data['page_number']
    if 'position_info' in data:
        update_data['position_info'] = data['position_info']
    if 'excerpt_type' in data:
        update_data['excerpt_type'] = data['excerpt_type']
    if 'rating' in data:
        update_data['rating'] = data['rating']
    if 'action_required' in data:
        update_data['action_required'] = data['action_required']
    
    note_repo.update(note_id, **update_data)
    note = note_repo.get_by_id(note_id)
    return success_response(note.to_dict(), '笔记更新成功')


@note_bp.route('/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = note_repo.get_by_id(note_id)
    if not note:
        return error_response('笔记不存在', 404)
    
    note_repo.delete(note_id)
    return success_response(message='笔记删除成功')
