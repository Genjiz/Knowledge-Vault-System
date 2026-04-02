from flask import Flask
from app.crawler.routes import crawl_task_bp, raw_issue_bp
from app.routes.health import health_bp
from app.routes.literature import literature_bp
from app.routes.tag import tag_bp
from app.routes.folder import folder_bp
from app.routes.note import note_bp
from app.routes.backup import backup_bp
from app.video_notes.routes import video_note_task_bp


def register_routes(app: Flask):
    app.register_blueprint(health_bp)
    app.register_blueprint(crawl_task_bp)
    app.register_blueprint(raw_issue_bp)
    app.register_blueprint(video_note_task_bp)
    app.register_blueprint(literature_bp)
    app.register_blueprint(tag_bp)
    app.register_blueprint(folder_bp)
    app.register_blueprint(note_bp)
    app.register_blueprint(backup_bp)
