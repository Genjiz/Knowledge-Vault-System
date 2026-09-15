from flask import Blueprint, current_app, request
from sqlalchemy import case, func

from app.analysis.models import PaperAnalysis
from app.analysis.services.analysis_service import (
    DEFAULT_PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_VERSION,
    PaperAnalysisService,
)
from app.core import error_response, paginated_response, success_response
from app.core.extensions import db
from app.core.tasks import TaskExecutor
from app.papers.models import Literature


paper_analysis_bp = Blueprint("paper_analysis", __name__, url_prefix="/api/paper-analyses")
_executor = TaskExecutor()


def _service():
    configured = current_app.config.get("PAPER_ANALYSIS_SERVICE")
    return configured or PaperAnalysisService()


def _submit(analysis_id):
    app = current_app._get_current_object()
    executor = current_app.config.get("PAPER_ANALYSIS_EXECUTOR") or _executor

    def run():
        with app.app_context():
            PaperAnalysisService().execute(analysis_id)

    def fail(exc):
        with app.app_context():
            PaperAnalysisService.fail(analysis_id, exc)

    executor.submit(analysis_id, run, on_error=fail)


@paper_analysis_bp.route("", methods=["GET"])
def list_analyses():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = PaperAnalysis.query.order_by(PaperAnalysis.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return paginated_response(
        [row.to_dict(include_content=False) for row in pagination.items],
        pagination.total,
        page,
        per_page,
    )


@paper_analysis_bp.route("/prompt-template", methods=["GET"])
def get_prompt_template():
    return success_response(
        {"version": PROMPT_TEMPLATE_VERSION, "content": DEFAULT_PROMPT_TEMPLATE}
    )


@paper_analysis_bp.route("/issues", methods=["GET"])
def list_issue_options():
    issue_text = func.lower(func.trim(func.coalesce(Literature.issue, "")))
    volume_text = func.lower(func.trim(func.coalesce(Literature.volume, "")))
    normalized_issue = case(
        (issue_text.in_(("", "year", "unassigned")), "unassigned"),
        else_=Literature.issue,
    )
    normalized_volume = case(
        (volume_text.in_(("", "unknown")), "unknown"),
        else_=Literature.volume,
    )
    rows = (
        db.session.query(
            func.max(Literature.journal_id),
            Literature.journal,
            Literature.year,
            normalized_volume,
            normalized_issue,
            func.count(Literature.id),
        )
        .filter(
            Literature.journal.isnot(None),
            Literature.journal != "",
            Literature.year.isnot(None),
        )
        .group_by(
            Literature.journal,
            Literature.year,
            normalized_volume,
            normalized_issue,
        )
        .order_by(
            Literature.journal,
            Literature.year.desc(),
            normalized_volume,
            normalized_issue,
        )
        .all()
    )
    return success_response(
        [
            {
                "journal_id": journal_id,
                "journal": journal,
                "year": year,
                "volume": volume or "unknown",
                "issue": issue,
                "paper_count": count,
            }
            for journal_id, journal, year, volume, issue, count in rows
        ]
    )


@paper_analysis_bp.route("/selection-preview", methods=["POST"])
def preview_selection():
    data = request.get_json() or {}
    papers = _service().select_literatures(data.get("literature_ids"), data.get("issues"))
    return success_response([paper.to_dict() for paper in papers])


@paper_analysis_bp.route("", methods=["POST"])
def create_analysis():
    data = request.get_json() or {}
    try:
        analysis = _service().create_analysis(
            literature_ids=data.get("literature_ids") or [],
            issues=data.get("issues") or [],
            title=data.get("title"),
            profile_id=data.get("profile_id"),
            custom_instruction=data.get("custom_instruction"),
            include_fulltext=bool(data.get("include_fulltext", False)),
        )
    except (TypeError, ValueError) as exc:
        return error_response(str(exc))
    _submit(analysis.id)
    return success_response(analysis.to_dict(include_items=True), "分析任务已创建")


@paper_analysis_bp.route("/<int:analysis_id>", methods=["GET"])
def get_analysis(analysis_id):
    analysis = db.session.get(PaperAnalysis, analysis_id)
    if analysis is None:
        return error_response("分析任务不存在", 404)
    return success_response(analysis.to_dict(include_items=True))


@paper_analysis_bp.route("/<int:analysis_id>", methods=["DELETE"])
def delete_analysis(analysis_id):
    analysis = db.session.get(PaperAnalysis, analysis_id)
    if analysis is None:
        return error_response("分析任务不存在", 404)
    db.session.delete(analysis)
    db.session.commit()
    return success_response({"id": analysis_id})


@paper_analysis_bp.route("/<int:analysis_id>/rerun", methods=["POST"])
def rerun_analysis(analysis_id):
    data = request.get_json() or {}
    try:
        analysis = _service().clone_analysis(analysis_id, data.get("profile_id"))
    except ValueError as exc:
        status = 404 if str(exc) == "分析任务不存在" else 400
        return error_response(str(exc), status)
    _submit(analysis.id)
    return success_response(analysis.to_dict(include_items=True), "重新分析任务已创建")
