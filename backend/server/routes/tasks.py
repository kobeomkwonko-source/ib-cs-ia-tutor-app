from flask import Blueprint, current_app, jsonify, request, send_file

from ..services import ServiceError, TaskService, TimeProvider
from ..utils.auth import require_role, require_user

tasks_bp = Blueprint("tasks", __name__)


def _get_task_service() -> TaskService:
    return TaskService(
        current_app.config["UPLOAD_FOLDER"],
        clock=TimeProvider(current_app.config.get("KST_OFFSET_HOURS", 9)),
    )


@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks():
    user, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    service = _get_task_service()
    try:
        tasks = service.list_tasks(user)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"tasks": tasks}), 200


@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json(silent=True)
    if data is None:
        data = request.form
    pdf = request.files.get("pdf")

    service = _get_task_service()
    try:
        service.create_task(teacher, data, pdf)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Task created successfully."}), 201


@tasks_bp.route("/tasks/<int:task_id>", methods=["PUT", "DELETE"])
def update_task(task_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_task_service()

    if request.method == "DELETE":
        try:
            deleted = service.delete_task(task_id)
        except ServiceError as exc:
            return jsonify({"success": False, "message": exc.message}), exc.status

        if not deleted:
            return jsonify({"success": False, "message": "Task not found."}), 404
        return jsonify({"success": True, "message": "Task deleted."}), 200

    data = request.get_json() or {}
    try:
        service.update_task(task_id, data, teacher)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Task updated successfully."}), 200


@tasks_bp.route("/tasks/<int:task_id>/assignments", methods=["GET"])
def get_task_assignments(task_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_task_service()
    try:
        student_ids = service.get_task_assignments(task_id)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"studentIds": student_ids}), 200


@tasks_bp.route("/tasks/<int:task_id>/file", methods=["GET"])
def download_task_file(task_id: int):
    user, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    service = _get_task_service()
    try:
        resolved_path = service.resolve_task_file_path(task_id, user)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return send_file(resolved_path, as_attachment=True)
