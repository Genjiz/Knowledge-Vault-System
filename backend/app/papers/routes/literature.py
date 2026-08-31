from flask import Blueprint, request, current_app
from app.papers.repositories import literature_repo
from app.core import success_response, error_response, paginated_response
from app.papers.models.tag import LiteratureTag
from app.papers.models.folder import LiteratureFolder
from app.core.extensions import db
from datetime import UTC, datetime
import os

literature_bp = Blueprint('literature', __name__, url_prefix='/api/literatures')


@literature_bp.route('', methods=['GET'])
def get_literatures():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status')
    language = request.args.get('language')
    year_start = request.args.get('year_start', type=int)
    year_end = request.args.get('year_end', type=int)
    tag_ids = request.args.getlist('tag_ids', type=int)
    folder_id = request.args.get('folder_id', type=int)
    has_pdf = request.args.get('has_pdf')
    title = request.args.get('title')
    authors = request.args.get('authors')
    abstract = request.args.get('abstract')
    journal_id = request.args.get('journal_id', type=int)
    
    if has_pdf is not None:
        has_pdf = has_pdf.lower() == 'true'
    
    pagination = literature_repo.filter(
        page=page,
        per_page=per_page,
        status=status,
        language=language,
        year_start=year_start,
        year_end=year_end,
        tag_ids=tag_ids if tag_ids else None,
        folder_id=folder_id,
        has_pdf=has_pdf,
        title=title,
        authors=authors,
        abstract=abstract,
        journal_id=journal_id
    )
    
    items = [item.to_dict() for item in pagination.items]
    return paginated_response(items, pagination.total, page, per_page)


@literature_bp.route('/<int:literature_id>', methods=['GET'])
def get_literature(literature_id):
    literature = literature_repo.get_by_id(literature_id)
    if not literature:
        return error_response('文献不存在', 404)
    return success_response(literature.to_dict())


@literature_bp.route('', methods=['POST'])
def create_literature():
    data = request.get_json()
    
    if not data.get('title') or not data.get('authors'):
        return error_response('标题和作者为必填项')
    
    if data.get('doi'):
        existing = literature_repo.check_duplicate_doi(data['doi'])
        if existing:
            return error_response(f'DOI已存在，文献ID: {existing.id}')
    
    literature = literature_repo.create(
        title=data['title'],
        authors=data['authors'],
        journal=data.get('journal'),
        year=data.get('year'),
        volume=data.get('volume'),
        issue=data.get('issue'),
        pages=data.get('pages'),
        doi=data.get('doi'),
        abstract=data.get('abstract'),
        keywords=data.get('keywords'),
        url=data.get('url'),
        language=data.get('language', 'en'),
        literature_type=data.get('literature_type', 'journal'),
        publisher=data.get('publisher'),
        status=data.get('status', '未读')
    )
    
    if data.get('tag_ids'):
        for tag_id in data['tag_ids']:
            db.session.add(LiteratureTag(literature_id=literature.id, tag_id=tag_id))
        db.session.commit()
    
    if data.get('folder_ids'):
        for folder_id in data['folder_ids']:
            db.session.add(LiteratureFolder(literature_id=literature.id, folder_id=folder_id))
        db.session.commit()
    
    return success_response(literature.to_dict(), '文献创建成功')


@literature_bp.route('/<int:literature_id>', methods=['PUT'])
def update_literature(literature_id):
    literature = literature_repo.get_by_id(literature_id)
    if not literature:
        return error_response('文献不存在', 404)
    
    data = request.get_json()
    
    if data.get('doi'):
        existing = literature_repo.check_duplicate_doi(data['doi'], exclude_id=literature_id)
        if existing:
            return error_response(f'DOI已存在，文献ID: {existing.id}')
    
    update_data = {}
    for field in ['title', 'authors', 'journal', 'year', 'volume', 'issue', 'pages', 
                   'doi', 'abstract', 'keywords', 'url', 'language', 'literature_type', 'publisher']:
        if field in data:
            update_data[field] = data[field]
    
    if 'status' in data and data['status'] != literature.status:
        update_data['status'] = data['status']
        update_data['status_changed_at'] = datetime.now(UTC)
    
    literature_repo.update(literature_id, **update_data)
    
    if 'tag_ids' in data:
        LiteratureTag.query.filter_by(literature_id=literature_id).delete()
        for tag_id in data['tag_ids']:
            db.session.add(LiteratureTag(literature_id=literature_id, tag_id=tag_id))
        db.session.commit()
    
    if 'folder_ids' in data:
        LiteratureFolder.query.filter_by(literature_id=literature_id).delete()
        for folder_id in data['folder_ids']:
            db.session.add(LiteratureFolder(literature_id=literature_id, folder_id=folder_id))
        db.session.commit()
    
    literature = literature_repo.get_by_id(literature_id)
    return success_response(literature.to_dict(), '文献更新成功')


@literature_bp.route('/<int:literature_id>', methods=['DELETE'])
def delete_literature(literature_id):
    literature = literature_repo.get_by_id(literature_id)
    if not literature:
        return error_response('文献不存在', 404)
    
    if literature.pdf_path:
        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            pdf_full_path = os.path.join(upload_folder, f'{literature_id}.pdf')
            if os.path.exists(pdf_full_path):
                os.remove(pdf_full_path)
        except Exception:
            pass
    
    literature_repo.delete(literature_id)
    return success_response(message='文献删除成功')


@literature_bp.route('/<int:literature_id>/pdf', methods=['POST'])
def upload_pdf(literature_id):
    literature = literature_repo.get_by_id(literature_id)
    if not literature:
        return error_response('文献不存在', 404)
    
    if 'file' not in request.files:
        return error_response('未上传文件')
    
    file = request.files['file']
    if file.filename == '':
        return error_response('未选择文件')
    
    if not file.filename.lower().endswith('.pdf'):
        return error_response('只支持PDF文件')
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    os.makedirs(upload_folder, exist_ok=True)
    
    filename = f'{literature_id}.pdf'
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    relative_path = f'uploads/pdfs/{filename}'
    literature_repo.update(literature_id, pdf_path=relative_path)
    
    return success_response({'pdf_path': relative_path}, 'PDF上传成功')


@literature_bp.route('/<int:literature_id>/pdf', methods=['DELETE'])
def delete_pdf(literature_id):
    literature = literature_repo.get_by_id(literature_id)
    if not literature:
        return error_response('文献不存在', 404)
    
    if literature.pdf_path:
        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            pdf_full_path = os.path.join(upload_folder, f'{literature_id}.pdf')
            if os.path.exists(pdf_full_path):
                os.remove(pdf_full_path)
        except Exception:
            pass
    
    literature_repo.update(literature_id, pdf_path=None)
    return success_response(message='PDF删除成功')


@literature_bp.route('/search', methods=['GET'])
def search_literatures():
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    if not keyword:
        return error_response('请输入搜索关键词')
    
    pagination = literature_repo.search(keyword, page, per_page)
    items = [item.to_dict() for item in pagination.items]
    return paginated_response(items, pagination.total, page, per_page)


@literature_bp.route('/statistics', methods=['GET'])
def get_statistics():
    stats = literature_repo.get_statistics()
    return success_response(stats)
