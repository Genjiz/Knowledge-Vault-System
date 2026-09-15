"""采集源注册表 API。

前端据此渲染采集源选项与每源的配置表单，新增采集源只需在注册表登记。
"""
from pathlib import Path

from flask import Blueprint, current_app, request

from app.collection.sources.registry import describe_sources
from app.collection.services.elsevier_key_service import ElsevierKeyService
from app.core import error_response, success_response

sources_bp = Blueprint("sources", __name__, url_prefix="/api/collection")


@sources_bp.route("/sources", methods=["GET"])
def list_sources():
    return success_response(describe_sources())


def _key_service():
    configured = current_app.config.get("COLLECTION_ENV_PATH")
    return ElsevierKeyService(Path(configured) if configured else None)


@sources_bp.route("/elsevier-key", methods=["GET"])
def get_elsevier_key():
    return success_response({"has_api_key": bool(_key_service().get())})


@sources_bp.route("/elsevier-key", methods=["PUT"])
def update_elsevier_key():
    data = request.get_json() or {}
    service = _key_service()
    if data.get("clear") is True:
        service.clear()
    else:
        try:
            service.set(data.get("api_key"))
        except ValueError as exc:
            return error_response(str(exc))
    return success_response({"has_api_key": bool(service.get())})
