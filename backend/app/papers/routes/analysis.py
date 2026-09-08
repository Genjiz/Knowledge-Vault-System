from flask import Blueprint, current_app, request
from sqlalchemy import func

from app.core import error_response, paginated_response, success_response
from app.core.extensions import db
from app.core.tasks import TaskExecutor
from app.papers.models import Literature
from app.papers.models.paper_analysis import PaperAnalysis
from app.papers.services.analysis_service import PaperAnalysisService

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


@paper_analysis_bp.route("/issues", methods=["GET"])
def list_issue_options():
    rows = (
        db.session.query(
            func.max(Literature.journal_id),
            Literature.journal,
            Literature.year,
            Literature.issue,
            func.count(Literature.id),
        )
        .filter(
            Literature.journal.isnot(None),
            Literature.journal != "",
            Literature.year.isnot(None),
            Literature.issue.isnot(None),
            Literature.issue != "",
        )
        .group_by(Literature.journal, Literature.year, Literature.issue)
        .order_by(Literature.journal, Literature.year.desc(), Literature.issue)
        .all()
    )
    return success_response(
        [
            {
                "journal_id": journal_id,
                "journal": journal,
                "year": year,
                "issue": issue,
                "paper_count": count,
            }
            for journal_id, journal, year, issue, count in rows
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
        return error_response(str(exc), 404)
    _submit(analysis.id)
    return success_response(analysis.to_dict(include_items=True), "重新分析任务已创建")
