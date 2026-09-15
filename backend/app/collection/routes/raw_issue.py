from flask import Blueprint, current_app, request

from app.collection.models import RawIssue, RawIssueAnalysis
from app.collection.sources.base import ProviderError
from app.collection.providers.translation_provider import TranslationProvider
from app.collection.services.analysis_service import AnalysisService
from app.collection.services.ingestion_service import IngestionService
from app.collection.services.raw_issue_service import RawIssueService
from app.collection.services.translation_service import TranslationService
from app.core.extensions import db
from app.core import error_response, paginated_response, success_response

raw_issue_bp = Blueprint("raw_issue", __name__, url_prefix="/api/raw-issues")


def _translation_service():
    return current_app.config.get("CRAWLER_TRANSLATION_SERVICE") or TranslationService(provider=TranslationProvider())


def _analysis_service():
    return current_app.config.get("CRAWLER_ANALYSIS_SERVICE")


def _raw_issue_service():
    return current_app.config.get("RAW_ISSUE_SERVICE") or RawIssueService()


def _ingestion_service():
    return current_app.config.get("CRAWLER_INGESTION_SERVICE") or IngestionService()


@raw_issue_bp.route("", methods=["GET"])
def list_raw_issues():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 500)
    pagination = RawIssue.query.order_by(RawIssue.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    items = [item.to_dict() for item in pagination.items]
    return paginated_response(items, pagination.total, page, per_page)


@raw_issue_bp.route("/<int:raw_issue_id>", methods=["GET"])
def get_raw_issue(raw_issue_id):
    raw_issue = db.session.get(RawIssue, raw_issue_id)
    if not raw_issue:
        return error_response("Raw issue not found", 404)
    payload = raw_issue.to_dict()
    payload["papers"] = [paper.to_dict() for paper in raw_issue.papers]
    return success_response(payload)


@raw_issue_bp.route("/<int:raw_issue_id>/papers", methods=["GET"])
def get_raw_issue_papers(raw_issue_id):
    raw_issue = db.session.get(RawIssue, raw_issue_id)
    if not raw_issue:
        return error_response("Raw issue not found", 404)
    return success_response([paper.to_dict() for paper in raw_issue.papers])


@raw_issue_bp.route("/<int:raw_issue_id>/refresh", methods=["POST"])
def refresh_raw_issue(raw_issue_id):
    raw_issue = db.session.get(RawIssue, raw_issue_id)
    if raw_issue is None:
        return error_response("Raw issue not found", 404)
    if raw_issue.source_type != "scopus":
        return error_response("当前仅支持重采 Scopus 卷期题录")
    try:
        task, raw_issues = _ingestion_service().run_ingestion(
            raw_issue.source_type,
            raw_issue.journal_name,
            raw_issue.year,
            "year",
            target_volume=raw_issue.volume,
            target_issue=raw_issue.issue,
        )
    except ProviderError as exc:
        return error_response(str(exc), 502)
    return success_response(
        {
            "task": task.to_dict(),
            "raw_issues": [item.to_dict() for item in raw_issues],
            "raw_issue": raw_issues[0].to_dict(),
        },
        "本期题录已重新采集",
    )


@raw_issue_bp.route("/<int:raw_issue_id>/translate", methods=["POST"])
def translate_raw_issue(raw_issue_id):
    service = _translation_service()
    if service is None:
        return error_response("Translation service is unavailable", 503)
    profile_id = (request.get_json(silent=True) or {}).get("profile_id")
    if profile_id in (None, ""):
        return error_response("请选择翻译模型")
    try:
        raw_issue = service.translate_issue(raw_issue_id, profile_id)
    except ValueError as exc:
        return error_response(str(exc))
    except ProviderError as exc:
        return error_response(str(exc), 502)
    except Exception as exc:
        return error_response(f"Translation failed: {exc}", 500)
    return success_response(raw_issue.to_dict())


@raw_issue_bp.route("/<int:raw_issue_id>/analyze", methods=["POST"])
def analyze_raw_issue(raw_issue_id):
    service = _analysis_service() or AnalysisService()
    profile_id = (request.get_json(silent=True) or {}).get("profile_id")
    if profile_id in (None, ""):
        return error_response("请选择分析模型")
    try:
        analysis = service.analyze_issue(raw_issue_id, profile_id)
    except ValueError as exc:
        return error_response(str(exc))
    except ProviderError as exc:
        return error_response(str(exc), 502)
    except Exception as exc:
        return error_response(f"Analysis failed: {exc}", 500)
    return success_response(analysis.to_dict())


@raw_issue_bp.route("/<int:raw_issue_id>/analysis", methods=["GET"])
def get_raw_issue_analysis(raw_issue_id):
    analysis = (
        RawIssueAnalysis.query.filter_by(raw_issue_id=raw_issue_id)
        .order_by(RawIssueAnalysis.created_at.desc())
        .first()
    )
    if not analysis:
        return success_response(None)
    return success_response(analysis.to_dict())


@raw_issue_bp.route("/<int:raw_issue_id>", methods=["DELETE"])
def delete_raw_issue(raw_issue_id):
    result = _raw_issue_service().delete_issue(raw_issue_id)
    if result is None:
        return error_response("Raw issue not found", 404)
    return success_response(result, "采集期号已删除")
