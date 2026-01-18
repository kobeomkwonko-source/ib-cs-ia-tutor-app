import math
import os
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ..db import get_db
from ..utils.auth import require_role, require_user

students_bp = Blueprint("students", __name__)


def _parse_datetime(value: str):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _calculate_penalty(points: int, deadline: datetime, submitted_at: datetime):
    if submitted_at <= deadline:
        return points, 0
    seconds_late = (submitted_at - deadline).total_seconds()
    days_late = math.ceil(seconds_late / 86400)
    if days_late >= 7:
        return 0, days_late
    penalized = int(points * (0.5 ** days_late))
    return max(0, penalized), days_late


def _add_attempt_numbers(submissions, key="student_id"):
    counts = {}
    for row in submissions:
        student_id = row.get(key)
        if student_id is None:
            continue
        counts[student_id] = counts.get(student_id, 0) + 1
        row["attempt_number"] = counts[student_id]


def _resolve_pdf_path(pdf_path: str):
    if not pdf_path:
        return None
    candidates = []
    if os.path.isabs(pdf_path):
        candidates.append(pdf_path)
    candidates.append(os.path.abspath(pdf_path))
    basename = os.path.basename(pdf_path)
    if basename:
        candidates.append(os.path.join(current_app.config["UPLOAD_FOLDER"], basename))
        candidates.append(
            os.path.abspath(os.path.join(current_app.config["UPLOAD_FOLDER"], basename))
        )
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


@students_bp.route("/submissions", methods=["POST"])
def create_submission():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    task_id = request.form.get("taskId")
    text_content = request.form.get("textContent")
    pdf = request.files.get("pdf")

    if not task_id:
        return jsonify({"success": False, "message": "taskId is required."}), 400

    if not text_content and not pdf:
        return jsonify({"success": False, "message": "Submission text or PDF is required."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM task_assignments WHERE task_id = %s AND student_id = %s",
        (task_id, student["id"]),
    )
    assignment = cursor.fetchone()
    if not assignment:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Task not assigned."}), 403

    cursor.execute(
        "SELECT id, deadline, points FROM tasks WHERE id = %s",
        (task_id,),
    )
    task = cursor.fetchone()
    if not task:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Task not found."}), 404

    pdf_path = None
    if pdf:
        filename = secure_filename(pdf.filename)
        if not filename.lower().endswith(".pdf"):
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Only PDF uploads are allowed."}), 400
        unique_name = f"{uuid.uuid4().hex}-{filename}"
        storage_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
        pdf.save(storage_path)
        pdf_path = unique_name

    submitted_at = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

    deadline_value = task["deadline"]
    if isinstance(deadline_value, str):
        deadline_value = _parse_datetime(deadline_value)
    submitted_value = _parse_datetime(submitted_at)
    max_points, days_late = _calculate_penalty(task["points"], deadline_value, submitted_value)

    cursor.execute(
        """
        INSERT INTO submissions (
            task_id,
            student_id,
            submitted_at,
            text_content,
            pdf_path,
            awarded_points,
            awarded_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            task_id,
            student["id"],
            submitted_at,
            text_content,
            pdf_path,
            None,
            None,
        ),
    )
    conn.commit()
    submission_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return (
        jsonify(
            {
                "success": True,
                "submissionId": submission_id,
                "maxPoints": max_points,
                "daysLate": days_late,
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
    conn = get_db()
    cursor = conn.cursor()

    if task_id:
        cursor.execute(
            """
            SELECT s.*, t.title, t.points, t.deadline
            FROM submissions s
            JOIN tasks t ON t.id = s.task_id
            WHERE s.student_id = %s AND s.task_id = %s
            ORDER BY s.submitted_at DESC
            """,
            (student["id"], task_id),
        )
    else:
        cursor.execute(
            """
            SELECT s.*, t.title, t.points, t.deadline
            FROM submissions s
            JOIN tasks t ON t.id = s.task_id
            WHERE s.student_id = %s
            ORDER BY s.submitted_at DESC
            """,
            (student["id"],),
        )

    submissions = cursor.fetchall()
    for row in submissions:
        deadline_value = row["deadline"]
        submitted_value = row["submitted_at"]
        if isinstance(deadline_value, str):
            deadline_value = _parse_datetime(deadline_value)
        if isinstance(submitted_value, str):
            submitted_value = _parse_datetime(submitted_value)
        max_points, days_late = _calculate_penalty(row["points"], deadline_value, submitted_value)
        row["max_points"] = max_points
        row["days_late"] = days_late
    _add_attempt_numbers(submissions)

    cursor.close()
    conn.close()
    return jsonify({"submissions": submissions}), 200


@students_bp.route("/tasks/<int:task_id>/submissions", methods=["GET"])
def list_task_submissions(task_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.*, u.username, u.email, t.points, t.deadline
        FROM submissions s
        JOIN users u ON u.id = s.student_id
        JOIN tasks t ON t.id = s.task_id
        WHERE s.task_id = %s
        ORDER BY s.submitted_at DESC
        """,
        (task_id,),
    )
    submissions = cursor.fetchall()
    for row in submissions:
        deadline_value = row["deadline"]
        submitted_value = row["submitted_at"]
        if isinstance(deadline_value, str):
            deadline_value = _parse_datetime(deadline_value)
        if isinstance(submitted_value, str):
            submitted_value = _parse_datetime(submitted_value)
        max_points, days_late = _calculate_penalty(row["points"], deadline_value, submitted_value)
        row["max_points"] = max_points
        row["days_late"] = days_late
    _add_attempt_numbers(submissions)

    cursor.close()
    conn.close()
    return jsonify({"submissions": submissions}), 200


@students_bp.route("/submissions/<int:submission_id>/award", methods=["POST"])
def award_submission(submission_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json()
    awarded_points = data.get("awardedPoints")
    teacher_comment = data.get("comment")

    if awarded_points is None:
        return jsonify({"success": False, "message": "awardedPoints is required."}), 400

    if awarded_points < 0:
        return jsonify({"success": False, "message": "awardedPoints must be non-negative."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.id, s.task_id, s.student_id, s.awarded_points, s.submitted_at, t.points, t.deadline
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        WHERE s.id = %s
        """,
        (submission_id,),
    )
    submission = cursor.fetchone()
    if not submission:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Submission not found."}), 404

    deadline_value = submission["deadline"]
    submitted_value = submission["submitted_at"]
    if isinstance(deadline_value, str):
        deadline_value = _parse_datetime(deadline_value)
    if isinstance(submitted_value, str):
        submitted_value = _parse_datetime(submitted_value)
    max_points, _ = _calculate_penalty(submission["points"], deadline_value, submitted_value)

    if awarded_points > max_points:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Points exceed penalty-adjusted max."}), 400

    cursor.execute(
        """
        SELECT id, awarded_points
        FROM submissions
        WHERE task_id = %s AND student_id = %s AND awarded_points IS NOT NULL AND id != %s
        LIMIT 1
        """,
        (submission["task_id"], submission["student_id"], submission_id),
    )
    other_awarded = cursor.fetchone()

    previous_points = submission["awarded_points"] or 0
    delta = awarded_points - previous_points

    if other_awarded:
        cursor.execute(
            """
            UPDATE submissions
            SET awarded_points = NULL,
                teacher_comment = NULL,
                awarded_at = NULL
            WHERE id = %s
            """,
            (other_awarded["id"],),
        )
        cursor.execute(
            "UPDATE users SET points = GREATEST(points - %s, 0) WHERE id = %s",
            (other_awarded["awarded_points"] or 0, submission["student_id"]),
        )

    cursor.execute(
        """
        UPDATE submissions
        SET awarded_points = %s,
            teacher_comment = %s,
            awarded_at = %s
        WHERE id = %s
        """,
        (
            awarded_points,
            teacher_comment,
            (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            submission_id,
        ),
    )
    cursor.execute(
        "UPDATE users SET points = GREATEST(points + %s, 0) WHERE id = %s",
        (delta, submission["student_id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Points awarded."}), 200


@students_bp.route("/tasks/<int:task_id>/students/<int:student_id>/award", methods=["POST"])
def award_task_submissions(task_id: int, student_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json()
    awarded_points = data.get("awardedPoints")
    teacher_comment = data.get("comment")

    if awarded_points is None:
        return jsonify({"success": False, "message": "awardedPoints is required."}), 400

    if awarded_points < 0:
        return jsonify({"success": False, "message": "awardedPoints must be non-negative."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.id, s.submitted_at, s.awarded_points, t.points, t.deadline
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        WHERE s.task_id = %s AND s.student_id = %s
        ORDER BY s.submitted_at DESC
        """,
        (task_id, student_id),
    )
    submissions = cursor.fetchall()

    if not submissions:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Submissions not found."}), 404

    latest = submissions[0]
    deadline_value = latest["deadline"]
    submitted_value = latest["submitted_at"]
    if isinstance(deadline_value, str):
        deadline_value = _parse_datetime(deadline_value)
    if isinstance(submitted_value, str):
        submitted_value = _parse_datetime(submitted_value)
    max_points, _ = _calculate_penalty(latest["points"], deadline_value, submitted_value)

    if awarded_points > max_points:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Points exceed penalty-adjusted max."}), 400

    previous_points = 0
    for row in submissions:
        if row["awarded_points"] is not None:
            previous_points = row["awarded_points"] or 0
            break

    delta = awarded_points - previous_points
    awarded_at = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE submissions
        SET awarded_points = %s,
            teacher_comment = %s,
            awarded_at = %s
        WHERE task_id = %s AND student_id = %s
        """,
        (awarded_points, teacher_comment, awarded_at, task_id, student_id),
    )
    cursor.execute(
        "UPDATE users SET points = GREATEST(points + %s, 0) WHERE id = %s",
        (delta, student_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Points awarded."}), 200


@students_bp.route("/submissions/<int:submission_id>/file", methods=["GET"])
def download_submission_file(submission_id: int):
    user, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT pdf_path, student_id FROM submissions WHERE id = %s",
        (submission_id,),
    )
    submission = cursor.fetchone()
    cursor.close()
    conn.close()

    if not submission or not submission["pdf_path"]:
        return jsonify({"success": False, "message": "File not found."}), 404

    resolved_path = _resolve_pdf_path(submission["pdf_path"])
    if not resolved_path:
        return jsonify({"success": False, "message": "File not found."}), 404

    if user["role"] == "student" and submission["student_id"] != user["id"]:
        return jsonify({"success": False, "message": "Forbidden."}), 403

    return send_file(resolved_path, as_attachment=True)


@students_bp.route("/leaderboard", methods=["GET"])
def leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id,
               u.username,
               COALESCE(earned.total_points, 0) AS total_points
        FROM users u
        LEFT JOIN (
            SELECT student_id, SUM(max_awarded) AS total_points
            FROM (
                SELECT student_id, task_id, MAX(awarded_points) AS max_awarded
                FROM submissions
                WHERE awarded_points IS NOT NULL
                GROUP BY student_id, task_id
            ) grouped
            GROUP BY student_id
        ) earned ON earned.student_id = u.id
        WHERE u.role = 'student'
        ORDER BY total_points DESC, u.username ASC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    leaderboard_rows = []
    current_rank = 0
    last_points = None
    for index, row in enumerate(rows):
        if last_points is None or row["total_points"] != last_points:
            current_rank = index + 1
            last_points = row["total_points"]
        leaderboard_rows.append(
            {
                "username": row["username"],
                "total_points": row["total_points"],
                "rank": current_rank,
            }
        )

    total_students = len(leaderboard_rows)
    for row in leaderboard_rows:
        row["tier"] = _assign_tier(row["rank"], total_students)

    return jsonify({"leaderboard": leaderboard_rows}), 200


def _assign_tier(rank: int, total: int):
    tiers = ["Challenger", "Master", "Diamond", "Gold", "Silver", "Bronze"]
    if total == 0:
        return "Bronze"
    if 1 <= rank <= len(tiers):
        return tiers[rank - 1]
    return "Bronze"


@students_bp.route("/student-progress", methods=["GET"])
def student_progress():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT t.id, t.title, t.description, t.deadline, t.points
        FROM tasks t
        JOIN task_assignments a ON a.task_id = t.id
        WHERE a.student_id = %s
        """,
        (student["id"],),
    )
    tasks = cursor.fetchall()

    cursor.execute(
        "SELECT task_id FROM submissions WHERE student_id = %s",
        (student["id"],),
    )
    submissions = cursor.fetchall()
    submitted_task_ids = {row["task_id"] for row in submissions}

    for task in tasks:
        task["status"] = "completed" if task["id"] in submitted_task_ids else "pending"

    cursor.close()
    conn.close()

    return jsonify({"success": True, "tasks": tasks, "points": student["points"]}), 200


@students_bp.route("/students/list", methods=["GET"])
def list_students():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, points FROM users WHERE role = 'student' ORDER BY username"
    )
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"students": students}), 200


@students_bp.route("/students/overview", methods=["GET"])
def students_overview():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, points FROM users WHERE role = 'student' ORDER BY username"
    )
    students = cursor.fetchall()

    cursor.execute(
        """
        SELECT a.student_id,
               t.id AS task_id,
               t.title,
               t.deadline,
               s.id AS submission_id,
               s.submitted_at
        FROM task_assignments a
        JOIN tasks t ON t.id = a.task_id
        LEFT JOIN (
            SELECT s1.id, s1.task_id, s1.student_id, s1.submitted_at
            FROM submissions s1
            JOIN (
                SELECT task_id, student_id, MAX(submitted_at) AS latest_submitted_at
                FROM submissions
                GROUP BY task_id, student_id
            ) latest
              ON latest.task_id = s1.task_id
             AND latest.student_id = s1.student_id
             AND latest.latest_submitted_at = s1.submitted_at
        ) s ON s.task_id = a.task_id AND s.student_id = a.student_id
        WHERE t.created_by = %s OR t.created_by IS NULL
        ORDER BY a.student_id, t.deadline IS NULL, t.deadline
        """,
        (teacher["id"],),
    )
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    tasks_by_student = {student["id"]: [] for student in students}
    for row in rows:
        tasks_by_student.setdefault(row["student_id"], []).append(
            {
                "id": row["task_id"],
                "title": row["title"],
                "deadline": row["deadline"],
                "submitted": row["submission_id"] is not None,
                "submitted_at": row["submitted_at"],
            }
        )

    overview = []
    for student in students:
        overview.append(
            {
                "id": student["id"],
                "username": student["username"],
                "email": student["email"],
                "points": student["points"],
                "tasks": tasks_by_student.get(student["id"], []),
            }
        )

    return jsonify({"students": overview}), 200
