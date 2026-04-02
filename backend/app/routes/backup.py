from datetime import UTC, datetime
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.literature import Literature
from app.models.tag import Tag, LiteratureTag
from app.models.folder import Folder, LiteratureFolder
from app.models.note import Note
from app.utils import success_response, error_response
from datetime import datetime
import json

backup_bp = Blueprint('backup', __name__, url_prefix='/api/backup')


@backup_bp.route('/export', methods=['GET'])
def export_data():
    literatures = Literature.query.all()
    tags = Tag.query.all()
    folders = Folder.query.all()
    notes = Note.query.all()
    literature_tags = LiteratureTag.query.all()
    literature_folders = LiteratureFolder.query.all()
    
    data = {
        'version': '1.0',
        'export_time': datetime.now(UTC).isoformat(),
        'literatures': [l.to_dict() for l in literatures],
        'tags': [t.to_dict() for t in tags],
        'folders': [f.to_dict() for f in folders],
        'notes': [n.to_dict() for n in notes],
        'literature_tags': [{'literature_id': lt.literature_id, 'tag_id': lt.tag_id} for lt in literature_tags],
        'literature_folders': [{'literature_id': lf.literature_id, 'folder_id': lf.folder_id} for lf in literature_folders]
    }
    
    return jsonify({
        'code': 200,
        'message': '导出成功',
        'data': data
    })


@backup_bp.route('/import', methods=['POST'])
def import_data():
    json_data = request.get_json()
    
    if not json_data or 'data' not in json_data:
        return error_response('无效的备份数据')
    
    data = json_data['data']
    mode = json_data.get('mode', 'merge')
    
    if mode == 'overwrite':
        Note.query.delete()
        LiteratureTag.query.delete()
        LiteratureFolder.query.delete()
        Literature.query.delete()
        Tag.query.delete()
        Folder.query.delete()
        db.session.commit()
    
    imported = 0
    
    tag_id_map = {}
    for tag_data in data.get('tags', []):
        existing = Tag.query.filter_by(name=tag_data['name']).first()
        if existing:
            tag_id_map[tag_data['id']] = existing.id
        else:
            tag = Tag(
                name=tag_data['name'],
                color=tag_data.get('color', '#409EFF')
            )
            db.session.add(tag)
            db.session.flush()
            tag_id_map[tag_data['id']] = tag.id
    
    folder_id_map = {}
    for folder_data in data.get('folders', []):
        existing = Folder.query.filter_by(name=folder_data['name'], parent_id=folder_data.get('parent_id')).first()
        if existing:
            folder_id_map[folder_data['id']] = existing.id
        else:
            folder = Folder(
                name=folder_data['name'],
                parent_id=folder_data.get('parent_id')
            )
            db.session.add(folder)
            db.session.flush()
            folder_id_map[folder_data['id']] = folder.id
    
    literature_id_map = {}
    for lit_data in data.get('literatures', []):
        existing = None
        if lit_data.get('doi'):
            existing = Literature.query.filter_by(doi=lit_data['doi']).first()
        
        if not existing:
            existing = Literature.query.filter_by(title=lit_data['title']).first()
        
        if existing:
            literature_id_map[lit_data['id']] = existing.id
        else:
            literature = Literature(
                title=lit_data['title'],
                authors=lit_data['authors'],
                journal=lit_data.get('journal'),
                year=lit_data.get('year'),
                volume=lit_data.get('volume'),
                issue=lit_data.get('issue'),
                pages=lit_data.get('pages'),
                doi=lit_data.get('doi'),
                abstract=lit_data.get('abstract'),
                keywords=lit_data.get('keywords'),
                pdf_path=lit_data.get('pdf_path'),
                url=lit_data.get('url'),
                language=lit_data.get('language', 'en'),
                literature_type=lit_data.get('literature_type', 'journal'),
                publisher=lit_data.get('publisher'),
                status=lit_data.get('status', '未读')
            )
            db.session.add(literature)
            db.session.flush()
            literature_id_map[lit_data['id']] = literature.id
            imported += 1
    
    for lt_data in data.get('literature_tags', []):
        old_lit_id = lt_data['literature_id']
        old_tag_id = lt_data['tag_id']
        
        new_lit_id = literature_id_map.get(old_lit_id)
        new_tag_id = tag_id_map.get(old_tag_id)
        
        if new_lit_id and new_tag_id:
            existing = LiteratureTag.query.filter_by(literature_id=new_lit_id, tag_id=new_tag_id).first()
            if not existing:
                db.session.add(LiteratureTag(literature_id=new_lit_id, tag_id=new_tag_id))
    
    for lf_data in data.get('literature_folders', []):
        old_lit_id = lf_data['literature_id']
        old_folder_id = lf_data['folder_id']
        
        new_lit_id = literature_id_map.get(old_lit_id)
        new_folder_id = folder_id_map.get(old_folder_id)
        
        if new_lit_id and new_folder_id:
            existing = LiteratureFolder.query.filter_by(literature_id=new_lit_id, folder_id=new_folder_id).first()
            if not existing:
                db.session.add(LiteratureFolder(literature_id=new_lit_id, folder_id=new_folder_id))
    
    for note_data in data.get('notes', []):
        old_lit_id = note_data['literature_id']
        new_lit_id = literature_id_map.get(old_lit_id)
        
        if new_lit_id:
            note = Note(
                literature_id=new_lit_id,
                type=note_data['type'],
                title=note_data.get('title'),
                content=note_data['content'],
                page_number=note_data.get('page_number'),
                position_info=note_data.get('position_info')
            )
            db.session.add(note)
    
    db.session.commit()
    
    return success_response({'imported': imported}, f'导入完成，共导入 {imported} 条文献')
