from sqlalchemy import text
from flask import Blueprint

from app.extensions import db
from app.utils import success_response

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check():
    db.session.execute(text("SELECT 1"))
    return success_response(
        {
            "status": "ok",
            "database": "ok",
        }
    )
