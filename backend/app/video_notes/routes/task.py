import threading
from pathlib import Path

from flask import Blueprint, current_app, request

from app.core import error_response, success_response
from app.video_notes.runtime.bilibili import extract_bvid, resolve_video_title
from app.video_notes.services.execution_service import ExecutionService
from app.video_notes.services.task_service import TaskService

video_note_task_bp = Blueprint("video_note_task", __name__, url_prefix="/api/video-note-tasks")


def _task_service():
    return current_app.config.get("VIDEO_NOTE_TASK_SERVICE") or TaskService()


def _run_task_in_app_context(app, task_id):
    with app.app_context():
        service = app.config.get("VIDEO_NOTE_EXECUTION_SERVICE") or ExecutionService()
        service.run_task(task_id)


def _task_executor():
    configured = current_app.config.get("VIDEO_NOTE_TASK_EXECUTOR")
    if configured:
        return configured

    app = current_app._get_current_object()

    def execute(task_id):
        thread = threading.Thread(
            target=_run_task_in_app_context,
            args=(app, task_id),
            daemon=True,
        )
        thread.start()

    return execute


def _read_text_if_exists(path_value):
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


@video_note_task_bp.route("", methods=["POST"])
def create_video_note_task():
    data = request.get_json() or {}
    source_url = (data.get("source_url") or "").strip()
    if not source_url:
        return error_response("Missing required field: source_url")

    try:
        bvid = extract_bvid(source_url)
    except ValueError as exc:
        return error_response(str(exc), 400)

    task = _task_service().create_task(
        source_url=source_url,
        platform="bilibili",
        bvid=bvid,
        video_title=resolve_video_title("", bvid, source_url),
        status="pending",
        current_step=None,
        whisper_model=(data.get("whisper_model") or "large-v3-turbo").strip(),
        language=(data.get("language") or "zh").strip(),
        device=(data.get("device") or "cuda").strip(),
        compute_type=(data.get("compute_type") or "int8_float16").strip(),
        use_vad=bool(data.get("use_vad", True)),
    )
    _task_executor()(task.id)
    return success_response(task.to_dict())


@video_note_task_bp.route("", methods=["GET"])
def list_video_note_tasks():
    tasks = [task.to_dict() for task in _task_service().task_repo.get_all()]
    return success_response(tasks)


@video_note_task_bp.route("/<int:task_id>", methods=["GET"])
def get_video_note_task(task_id):
    task = _task_service().task_repo.get_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    payload = task.to_dict()
    payload["transcript_content"] = _read_text_if_exists(task.transcript_path)
    payload["note_content"] = _read_text_if_exists(task.note_path)
    return success_response(payload)


@video_note_task_bp.route("/<int:task_id>/logs", methods=["GET"])
def get_video_note_task_logs(task_id):
    task = _task_service().task_repo.get_by_id(task_id)
    if not task:
        return error_response("Task not found", 404)
    return success_response([log.to_dict() for log in task.logs])
