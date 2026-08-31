from flask import Blueprint, request
from app.papers.repositories import tag_repo
from app.core import success_response, error_response

tag_bp = Blueprint('tag', __name__, url_prefix='/api/tags')


@tag_bp.route('', methods=['GET'])
def get_tags():
    tags = tag_repo.get_with_literature_count()
    return success_response(tags)


@tag_bp.route('/<int:tag_id>', methods=['GET'])
def get_tag(tag_id):
    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        return error_response('标签不存在', 404)
    return success_response(tag.to_dict())


@tag_bp.route('', methods=['POST'])
def create_tag():
    data = request.get_json()
    
    if not data.get('name'):
        return error_response('标签名称为必填项')
    
    existing = tag_repo.get_by_name(data['name'])
    if existing:
        return error_response('标签名称已存在')
    
    tag = tag_repo.create(
        name=data['name'],
        color=data.get('color', '#409EFF')
    )
    return success_response(tag.to_dict(), '标签创建成功')


@tag_bp.route('/<int:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        return error_response('标签不存在', 404)
    
    data = request.get_json()
    
    if data.get('name') and data['name'] != tag.name:
        existing = tag_repo.get_by_name(data['name'])
        if existing:
            return error_response('标签名称已存在')
    
    update_data = {}
    if 'name' in data:
        update_data['name'] = data['name']
    if 'color' in data:
        update_data['color'] = data['color']
    
    tag_repo.update(tag_id, **update_data)
    tag = tag_repo.get_by_id(tag_id)
    return success_response(tag.to_dict(), '标签更新成功')


@tag_bp.route('/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        return error_response('标签不存在', 404)
    
    tag_repo.delete(tag_id)
    return success_response(message='标签删除成功')
