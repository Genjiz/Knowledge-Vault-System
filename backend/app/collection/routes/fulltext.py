from flask import Blueprint, current_app, request

from app.collection.models import FullTextTask
from app.collection.services.fulltext_service import (
    FullTextConflictError,
    FullTextError,
    FullTextService,
)
from app.core import error_response, success_response
from app.core.extensions import db
from app.core.tasks import TaskExecutor


fulltext_task_bp = Blueprint("fulltext_task", __name__)
_DEFAULT_EXECUTOR = TaskExecutor()


def get_fulltext_service():
    return current_app.config.get("FULLTEXT_SERVICE") or FullTextService()


def _run_in_app_context(app, task_id):
    with app.app_context():
        service = app.config.get("FULLTEXT_SERVICE") or FullTextService()
        service.run_task(task_id)


def _mark_failed_in_app_context(app, task_id, exc):
    with app.app_context():
        service = app.config.get("FULLTEXT_SERVICE") or FullTextService()
        service.mark_failed(task_id, exc)


def schedule_fulltext_task(task_id):
    configured = current_app.config.get("FULLTEXT_TASK_EXECUTOR")
    if configured:
        configured(task_id)
        return
    app = current_app._get_current_object()
    _DEFAULT_EXECUTOR.submit(
        task_id,
        lambda: _run_in_app_context(app, task_id),
        on_error=lambda exc: _mark_failed_in_app_context(app, task_id, exc),
    )


def _create_response(factory):
    try:
        task = factory()
    except FullTextConflictError as exc:
        return error_response(str(exc), 409)
    except FullTextError as exc:
        return error_response(str(exc), 400)
    if getattr(task, "_was_created", True):
        schedule_fulltext_task(task.id)
    return success_response(task.to_dict())


@fulltext_task_bp.route("/api/literatures/<int:literature_id>/fulltext-tasks", methods=["POST"])
def create_literature_fulltext_task(literature_id):
    data = request.get_json(silent=True) or {}
    return _create_response(
        lambda: get_fulltext_service().create_single_task(
            literature_id,
            replace_existing=bool(data.get("replace_existing", False)),
        )
    )


@fulltext_task_bp.route("/api/raw-issues/<int:raw_issue_id>/fulltext-tasks", methods=["POST"])
def create_issue_fulltext_task(raw_issue_id):
    return _create_response(lambda: get_fulltext_service().create_issue_task(raw_issue_id))


@fulltext_task_bp.route("/api/fulltext-tasks", methods=["GET"])
def list_fulltext_tasks():
    literature_id = request.args.get("literature_id", type=int)
    raw_issue_id = request.args.get("raw_issue_id", type=int)
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
    tasks = get_fulltext_service().list_tasks(
        literature_id=literature_id,
        raw_issue_id=raw_issue_id,
        limit=limit,
    )
    return success_response([task.to_dict() for task in tasks])


@fulltext_task_bp.route("/api/fulltext-tasks/<int:task_id>", methods=["GET"])
def get_fulltext_task(task_id):
    task = db.session.get(FullTextTask, task_id)
    if task is None:
        return error_response("全文任务不存在", 404)
    return success_response(task.to_dict())


@fulltext_task_bp.route("/api/fulltext-tasks/<int:task_id>/resume", methods=["POST"])
def resume_fulltext_task(task_id):
    try:
        task = get_fulltext_service().resume_task(task_id)
    except FullTextConflictError as exc:
        return error_response(str(exc), 409)
    except FullTextError as exc:
        return error_response(str(exc), 404)
    schedule_fulltext_task(task.id)
    return success_response(task.to_dict())
