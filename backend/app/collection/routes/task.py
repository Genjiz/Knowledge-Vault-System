from flask import Blueprint, current_app, request

from app.collection.sources.base import ProviderError
from app.collection.services.ingestion_service import IngestionService
from app.collection.services.task_service import TaskService
from app.collection.sources.registry import describe_source
from app.core import error_response, success_response

crawl_task_bp = Blueprint("crawl_task", __name__, url_prefix="/api/crawl-tasks")


def _ingestion_service():
    return current_app.config.get("CRAWLER_INGESTION_SERVICE") or IngestionService()


def _task_service():
    return current_app.config.get("CRAWLER_TASK_SERVICE") or TaskService()


@crawl_task_bp.route("", methods=["POST"])
def create_crawl_task():
    data = request.get_json() or {}
    source_meta = describe_source(data.get("source_type"))
    required_fields = ["source_type", "journal_name", "year"]
    if not source_meta or source_meta["ingest_scope"] != "year":
        required_fields.append("issue")
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    download_fulltext = bool(data.get("download_fulltext", False))
    if download_fulltext and not (
        source_meta and source_meta["capabilities"].get("download_pdf")
    ):
        return error_response("当前采集源不支持全文下载")

    try:
        task, raw_issues = _ingestion_service().run_ingestion(
            source_type=data["source_type"],
            journal_name=data["journal_name"],
            year=data["year"],
            issue=(
                "year"
                if source_meta and source_meta["ingest_scope"] == "year"
                else str(data["issue"])
            ),
        )
    except ProviderError as exc:
        return error_response(str(exc), 502)
    except Exception as exc:
        return error_response(f"Crawl task failed: {exc}", 500)

    if not isinstance(raw_issues, (list, tuple)):
        raw_issues = [raw_issues]
    result = {
        "task": task.to_dict(),
        "raw_issues": [raw_issue.to_dict() for raw_issue in raw_issues],
        # 兼容旧客户端；新客户端应使用 raw_issues。
        "raw_issue": raw_issues[0].to_dict() if raw_issues else None,
    }
    if download_fulltext:
        try:
            from app.collection.routes.fulltext import (
                get_fulltext_service,
                schedule_fulltext_task,
            )

            if len(raw_issues) != 1:
                raise ValueError("全文补采要求题录任务只产生一个期号")
            fulltext_task = get_fulltext_service().create_issue_task(
                raw_issues[0].id,
                mode="after_ingestion",
            )
            if getattr(fulltext_task, "_was_created", True):
                schedule_fulltext_task(fulltext_task.id)
            result["fulltext_task"] = fulltext_task.to_dict()
        except Exception as exc:
            result["fulltext_error"] = str(exc)

    return success_response(result)


@crawl_task_bp.route("", methods=["GET"])
def list_crawl_tasks():
    tasks = [task.to_dict() for task in _task_service().task_repo.get_all()]
    return success_response(tasks)


@crawl_task_bp.route("/<int:task_id>", methods=["GET"])
def get_crawl_task(task_id):
    task = _task_service().task_repo.get_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    return success_response(task.to_dict())


@crawl_task_bp.route("/<int:task_id>/logs", methods=["GET"])
def get_crawl_task_logs(task_id):
    task = _task_service().task_repo.get_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    return success_response([log.to_dict() for log in task.logs])
