from datetime import UTC, datetime

from flask import Blueprint, current_app, request
from sqlalchemy.exc import IntegrityError

from app.core import error_response, success_response
from app.core.extensions import db
from app.core.llm.errors import LLMError
from app.core.llm.models import LLMProfile
from app.core.llm.secrets import EnvSecretStore
from app.core.llm.service import LLMService

llm_bp = Blueprint("llm", __name__, url_prefix="/api/llm")
PROTOCOLS = {"gemini", "openai"}


def _secret_store():
    return current_app.config.get("LLM_SECRET_STORE") or EnvSecretStore()


def _payload(profile):
    has_key = bool(_secret_store().get(profile.id))
    if not has_key and profile.protocol == "gemini":
        try:
            from app.core.llm.gemini import load_gemini_api_key

            has_key = bool(load_gemini_api_key())
        except Exception:
            has_key = False
    return profile.to_dict(has_api_key=has_key)


def _validate(data, profile=None):
    name = str(data.get("name", profile.name if profile else "") or "").strip()
    protocol = str(data.get("protocol", profile.protocol if profile else "") or "").strip()
    model_name = str(data.get("model_name", profile.model_name if profile else "") or "").strip()
    base_url = str(data.get("base_url", profile.base_url if profile else "") or "").strip()
    if not name:
        return None, "名称为必填项"
    if protocol not in PROTOCOLS:
        return None, "protocol 仅支持 gemini 或 openai"
    if not model_name:
        return None, "模型名称为必填项"
    if protocol == "openai" and not base_url:
        return None, "OpenAI Compatible 模型必须配置 base_url"
    return {
        "name": name,
        "protocol": protocol,
        "model_name": model_name,
        "base_url": base_url or None,
        "enabled": bool(data.get("enabled", profile.enabled if profile else True)),
    }, None


@llm_bp.route("/profiles", methods=["GET"])
def list_profiles():
    profiles = LLMProfile.query.order_by(LLMProfile.name).all()
    return success_response([_payload(profile) for profile in profiles])


@llm_bp.route("/profiles", methods=["POST"])
def create_profile():
    data = request.get_json() or {}
    values, error = _validate(data)
    if error:
        return error_response(error)
    profile = LLMProfile(**values)
    db.session.add(profile)
    try:
        db.session.flush()
        api_key = str(data.get("api_key") or "").strip()
        if api_key:
            _secret_store().set(profile.id, api_key)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("模型档案名称已存在", 409)
    except Exception as exc:
        db.session.rollback()
        if profile.id:
            _secret_store().delete(profile.id)
        return error_response(f"保存模型档案失败：{exc}", 500)
    return success_response(_payload(profile))


@llm_bp.route("/profiles/<int:profile_id>", methods=["PUT"])
def update_profile(profile_id):
    profile = db.session.get(LLMProfile, profile_id)
    if profile is None:
        return error_response("模型档案不存在", 404)
    data = request.get_json() or {}
    values, error = _validate(data, profile)
    if error:
        return error_response(error)
    for key, value in values.items():
        setattr(profile, key, value)
    api_key = str(data.get("api_key") or "").strip()
    if data.get("clear_api_key"):
        _secret_store().delete(profile.id)
    elif api_key:
        _secret_store().set(profile.id, api_key)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("模型档案名称已存在", 409)
    return success_response(_payload(profile))


@llm_bp.route("/profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    profile = db.session.get(LLMProfile, profile_id)
    if profile is None:
        return error_response("模型档案不存在", 404)
    _secret_store().delete(profile.id)
    db.session.delete(profile)
    db.session.commit()
    return success_response({"id": profile_id})


@llm_bp.route("/profiles/<int:profile_id>/test", methods=["POST"])
def test_profile(profile_id):
    profile = db.session.get(LLMProfile, profile_id)
    if profile is None:
        return error_response("模型档案不存在", 404)
    try:
        LLMService().test_profile(profile)
        profile.last_check_status = "ok"
        profile.last_check_message = "连接成功"
    except Exception as exc:
        message = str(exc)
        api_key = _secret_store().get(profile.id)
        if api_key:
            message = message.replace(api_key, "***")
        profile.last_check_status = "failed"
        profile.last_check_message = message
    profile.last_checked_at = datetime.now(UTC)
    db.session.commit()
    return success_response(_payload(profile))
