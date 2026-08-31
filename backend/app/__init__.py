import os
from flask import Flask, send_from_directory
from config import config
from app.core.extensions import db, cors, migrate


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    cors.init_app(app)
    migrate.init_app(app, db)
    
    upload_folder = app.config.get('UPLOAD_FOLDER')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    from app.papers.models import Literature, Tag, LiteratureTag, Folder, LiteratureFolder, Note
    from app.collection.models import CrawlTask, CrawlTaskLog, LLMRun, RawIssue, RawIssueAnalysis, RawPaper
    from app.video_notes.models import VideoNoteTask, VideoNoteTaskLog
    
    @app.route('/uploads/pdfs/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(upload_folder, filename)
    
    from app.papers.routes import register_routes
    register_routes(app)

    from app.core.errors import register_error_handlers
    register_error_handlers(app)

    return app
