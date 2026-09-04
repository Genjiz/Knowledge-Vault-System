"""采集源注册表 API。

前端据此渲染采集源选项与每源的配置表单，新增采集源只需在注册表登记。
"""
from flask import Blueprint

from app.collection.sources.registry import describe_sources
from app.core import success_response

sources_bp = Blueprint("sources", __name__, url_prefix="/api/collection")


@sources_bp.route("/sources", methods=["GET"])
def list_sources():
    return success_response(describe_sources())
