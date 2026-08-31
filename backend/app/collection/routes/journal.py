"""期刊与采集源配置 API（T-1/T-5 数据基础）。"""
from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from app.core import error_response, success_response
from app.core.extensions import db
from app.papers.models import Journal, JournalSourceConfig

SUPPORTED_SOURCE_IDS = {"ncpssd", "elsevier", "cnki", "official"}

journal_bp = Blueprint("journal", __name__, url_prefix="/api/journals")


@journal_bp.route("", methods=["GET"])
def list_journals():
    journals = Journal.query.order_by(Journal.name).all()
    return success_response([journal.to_dict() for journal in journals])


@journal_bp.route("", methods=["POST"])
def create_journal():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error_response("期刊名称为必填项")

    if Journal.query.filter_by(name=name).first():
        return error_response("期刊已存在", 409)

    journal = Journal(
        name=name,
        issn=data.get("issn"),
        publisher=data.get("publisher"),
    )
    db.session.add(journal)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("期刊已存在", 409)
    return success_response(journal.to_dict())


@journal_bp.route("/<int:journal_id>/sources", methods=["PUT"])
def update_journal_source(journal_id):
    data = request.get_json() or {}
    source_id = data.get("source_id")
    if not source_id:
        return error_response("source_id 为必填项")
    if source_id not in SUPPORTED_SOURCE_IDS:
        return error_response(f"不支持的采集源：{source_id}，可选值：{sorted(SUPPORTED_SOURCE_IDS)}")

    journal = db.session.get(Journal, journal_id)
    if journal is None:
        return error_response("期刊不存在", 404)

    config = JournalSourceConfig.query.filter_by(journal_id=journal_id, source_id=source_id).first()
    if config is None:
        config = JournalSourceConfig(journal_id=journal_id, source_id=source_id)
        db.session.add(config)

    config.enabled = bool(data.get("enabled", True))
    if "config" in data:
        import json

        config.config_json = json.dumps(data["config"], ensure_ascii=False) if data["config"] else None
    db.session.commit()
    return success_response(config.to_dict())
