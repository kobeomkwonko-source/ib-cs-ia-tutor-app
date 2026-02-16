from flask import Blueprint, current_app, jsonify, request, send_file

from ..services import (
    ServiceError,
    StudentService,
    SubmissionService,
    TimeProvider,
)
from ..utils.auth import require_role, require_user

students_bp = Blueprint("students", __name__)


def _get_submission_service() -> SubmissionService:
    return SubmissionService(
        current_app.config["UPLOAD_FOLDER"],
        clock=TimeProvider(current_app.config.get("KST_OFFSET_HOURS", 9)),
    )


def _get_student_service() -> StudentService:
    return StudentService()


@students_bp.route("/submissions", methods=["POST"])
def create_submission():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    task_id = request.form.get("taskId")
    text_content = request.form.get("textContent")
    pdf = request.files.get("pdf")

    service = _get_submission_service()
    try:
        result = service.create_submission(student, task_id, text_content, pdf)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return (
        jsonify(
            {
                "success": True,
                "submissionId": result["submissionId"],
                "maxPoints": result["maxPoints"],
                "daysLate": result["daysLate"],
                "message": "Submission received.",
            }
        ),
        201,
    )


@students_bp.route("/submissions", methods=["GET"])
def list_my_submissions():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    task_id = request.args.get("taskId")

    service = _get_submission_service()
    try:
        submissions = service.list_my_submissions(student, task_id)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"submissions": submissions}), 200


@students_bp.route("/tasks/<int:task_id>/submissions", methods=["GET"])
def list_task_submissions(task_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_submission_service()
    try:
        submissions = service.list_task_submissions(task_id)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"submissions": submissions}), 200


@students_bp.route("/submissions/<int:submission_id>/award", methods=["POST"])
def award_submission(submission_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json() or {}
    awarded_points = data.get("awardedPoints")
    teacher_comment = data.get("comment")

    service = _get_submission_service()
    try:
        service.award_submission(teacher, submission_id, awarded_points, teacher_comment)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Points awarded."}), 200


@students_bp.route("/tasks/<int:task_id>/students/<int:student_id>/award", methods=["POST"])
def award_task_submissions(task_id: int, student_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json() or {}
    awarded_points = data.get("awardedPoints")
    teacher_comment = data.get("comment")

    service = _get_submission_service()
    try:
        service.award_task_submissions(
            task_id, student_id, awarded_points, teacher_comment
        )
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Points awarded."}), 200


@students_bp.route("/submissions/<int:submission_id>/file", methods=["GET"])
def download_submission_file(submission_id: int):
    user, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    service = _get_submission_service()
    try:
        resolved_path = service.resolve_submission_file_path(user, submission_id)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return send_file(resolved_path, as_attachment=True)


@students_bp.route("/submissions/<int:submission_id>", methods=["DELETE"])
def delete_submission(submission_id: int):
    user, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    service = _get_submission_service()
    try:
        service.delete_submission(user, submission_id)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Submission deleted."}), 200


@students_bp.route("/leaderboard", methods=["GET"])
def leaderboard():
    service = _get_student_service()
    leaderboard_rows = service.leaderboard()
    return jsonify({"leaderboard": leaderboard_rows}), 200


@students_bp.route("/student-progress", methods=["GET"])
def student_progress():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_student_service()
    progress = service.student_progress(student)
    return jsonify({"success": True, "tasks": progress["tasks"], "points": progress["points"]}), 200


@students_bp.route("/students/list", methods=["GET"])
def list_students():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_student_service()
    students = service.list_students()
    return jsonify({"students": students}), 200


@students_bp.route("/students/overview", methods=["GET"])
def students_overview():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_student_service()
    overview = service.students_overview(teacher["id"])
    return jsonify({"students": overview}), 200
