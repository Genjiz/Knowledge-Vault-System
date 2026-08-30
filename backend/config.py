import os

from app.core.paths import crawler_artifacts_root, database_uri, upload_folder

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'knowledge-vault-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ARTIFACT_ROOT = os.environ.get('ARTIFACT_ROOT') or str(crawler_artifacts_root())
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or str(upload_folder())
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
