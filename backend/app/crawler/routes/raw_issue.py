from flask import Blueprint, current_app

from app.crawler.models import RawIssue, RawIssueAnalysis
from app.crawler.providers.base import ProviderError
from app.crawler.providers.translation_provider import TranslationProvider
from app.crawler.services.analysis_service import AnalysisService
from app.crawler.services.translation_service import TranslationService
from app.extensions import db
from app.utils import error_response, paginated_response, success_response

raw_issue_bp = Blueprint("raw_issue", __name__, url_prefix="/api/raw-issues")


def _translation_service():
    return current_app.config.get("CRAWLER_TRANSLATION_SERVICE") or TranslationService(provider=TranslationProvider())


def _analysis_service():
    return current_app.config.get("CRAWLER_ANALYSIS_SERVICE")


@raw_issue_bp.route("", methods=["GET"])
def list_raw_issues():
    page = 1
    per_page = 20
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


@raw_issue_bp.route("/<int:raw_issue_id>/translate", methods=["POST"])
def translate_raw_issue(raw_issue_id):
    service = _translation_service()
    if service is None:
        return error_response("Translation service is unavailable", 503)
    try:
        raw_issue = service.translate_issue(raw_issue_id)
    except ProviderError as exc:
        return error_response(str(exc), 502)
    except Exception as exc:
        return error_response(f"Translation failed: {exc}", 500)
    return success_response(raw_issue.to_dict())


@raw_issue_bp.route("/<int:raw_issue_id>/analyze", methods=["POST"])
def analyze_raw_issue(raw_issue_id):
    service = _analysis_service() or AnalysisService()
    try:
        analysis = service.analyze_issue(raw_issue_id)
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
