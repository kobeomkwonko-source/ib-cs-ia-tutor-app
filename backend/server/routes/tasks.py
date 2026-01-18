import math
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..utils.auth import require_role, require_user

tasks_bp = Blueprint("tasks", __name__)


def _parse_datetime(value):
    """
    Normalize various datetime string shapes into a naive datetime object.
    Accepts MySQL style ('YYYY-MM-DD HH:MM:SS'), ISO strings with or without 'T',
    and RFC style strings that Flask may emit when JSON serializing datetimes.
    """
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("Unsupported datetime type")

    normalized = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue

    try:
        # Handles most ISO-8601 strings (e.g., fromisoformat understands 'YYYY-MM-DD HH:MM:SS')
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass

    try:
        # Fallback for RFC 2822/1123 style strings (e.g., 'Fri, 16 Jan 2026 00:00:00 GMT')
        return parsedate_to_datetime(normalized).replace(tzinfo=None)
    except Exception as exc:
        raise ValueError(f"Invalid datetime format: {value}") from exc


def _normalize_deadline_input(deadline_raw):
    if deadline_raw is None:
        return None
    try:
        parsed = _parse_datetime(deadline_raw)
    except ValueError:
        return None
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _calculate_penalty(points: int, deadline: datetime, submitted_at: datetime):
    if submitted_at <= deadline:
        return points
    seconds_late = (submitted_at - deadline).total_seconds()
    days_late = math.ceil(seconds_late / 86400)
    if days_late >= 7:
        return 0
    penalized = int(points * (0.5 ** days_late))
    return max(0, penalized)

def _normalize_student_ids(value):
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    normalized = []
    for entry in value:
        try:
            normalized.append(int(entry))
        except (TypeError, ValueError):
            return None
    return normalized


def _fetch_valid_student_ids(conn, student_ids):
    if not student_ids:
        return []
    placeholders = ", ".join(["%s"] * len(student_ids))
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id FROM users WHERE role = 'student' AND id IN ({placeholders})",
        student_ids,
    )
    rows = cursor.fetchall()
    cursor.close()
    return {row["id"] for row in rows}


def _replace_task_assignments(conn, task_id: int, student_ids, teacher_id: int):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM task_assignments WHERE task_id = %s", (task_id,))
    if student_ids:
        rows = [(task_id, student_id, teacher_id) for student_id in student_ids]
        cursor.executemany(
            """
            INSERT INTO task_assignments (task_id, student_id, assigned_by)
            VALUES (%s, %s, %s)
            """,
            rows,
        )
    conn.commit()
    cursor.close()


def _serialize_deadline(task):
    if not task.get("deadline"):
        return
    try:
        task["deadline"] = _parse_datetime(task["deadline"]).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        task["deadline"] = None


@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks():
    user, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()

    if user["role"] == "student":
        cursor.execute(
            """
            SELECT t.id, t.title, t.description, t.deadline, t.points, t.difficulty, t.created_by
            FROM tasks t
            JOIN task_assignments a ON a.task_id = t.id
            WHERE a.student_id = %s
            ORDER BY t.deadline IS NULL, t.deadline
            """,
            (user["id"],),
        )
        tasks = cursor.fetchall()
        cursor.execute(
            "SELECT DISTINCT task_id FROM submissions WHERE student_id = %s",
            (user["id"],),
        )
        submitted = {row["task_id"] for row in cursor.fetchall()}
        for task in tasks:
            if not task.get("difficulty"):
                task["difficulty"] = "medium"
            task["is_done"] = task["id"] in submitted
            _serialize_deadline(task)
    else:
        cursor.execute(
            "SELECT id, title, description, deadline, points, difficulty, created_by FROM tasks ORDER BY deadline IS NULL, deadline"
        )
        tasks = cursor.fetchall()
        for task in tasks:
            if not task.get("difficulty"):
                task["difficulty"] = "medium"
            task["is_done"] = False
            _serialize_deadline(task)

    cursor.close()
    conn.close()
    return jsonify({"tasks": tasks}), 200


@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    deadline = data.get("deadline")
    points = data.get("points")
    difficulty = data.get("difficulty", "medium")
    assigned_student_ids = _normalize_student_ids(data.get("assignedStudentIds"))

    if not title:
        return jsonify({"success": False, "message": "Title is required."}), 400

    if not description:
        return jsonify({"success": False, "message": "Description is required."}), 400

    if not deadline:
        return jsonify({"success": False, "message": "Deadline is required."}), 400

    if points is None:
        return jsonify({"success": False, "message": "Points are required."}), 400

    if assigned_student_ids is None or len(assigned_student_ids) == 0:
        return (
            jsonify({"success": False, "message": "Select at least one student."}),
            400,
        )

    try:
        points_value = int(points)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Points must be a number."}), 400

    deadline_value = _normalize_deadline_input(deadline)
    if not deadline_value:
        return jsonify({"success": False, "message": "Invalid deadline format."}), 400

    if difficulty not in ["easy", "medium", "hard"]:
        return jsonify({"success": False, "message": "Invalid difficulty."}), 400

    conn = get_db()
    cursor = conn.cursor()
    valid_student_ids = _fetch_valid_student_ids(conn, assigned_student_ids)
    if len(valid_student_ids) != len(set(assigned_student_ids)):
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Invalid student list."}), 400

    cursor.execute(
        "INSERT INTO tasks (title, description, deadline, points, difficulty, created_by) VALUES (%s, %s, %s, %s, %s, %s)",
        (title, description, deadline_value, points_value, difficulty, teacher["id"]),
    )
    conn.commit()
    task_id = cursor.lastrowid
    cursor.close()
    _replace_task_assignments(conn, task_id, assigned_student_ids, teacher["id"])
    conn.close()

    return jsonify({"success": True, "message": "Task created successfully."}), 201


@tasks_bp.route("/tasks/<int:task_id>", methods=["PUT", "DELETE"])
def update_task(task_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    if request.method == "DELETE":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        deleted = cursor.rowcount
        cursor.close()
        conn.close()
        if deleted == 0:
            return jsonify({"success": False, "message": "Task not found."}), 404
        return jsonify({"success": True, "message": "Task deleted."}), 200

    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    deadline = data.get("deadline")
    points = data.get("points")
    difficulty = data.get("difficulty")
    assigned_student_ids = None
    if "assignedStudentIds" in data:
        assigned_student_ids = _normalize_student_ids(data.get("assignedStudentIds"))
        if assigned_student_ids is None or len(assigned_student_ids) == 0:
            return (
                jsonify({"success": False, "message": "Select at least one student."}),
                400,
            )
    if difficulty is not None and difficulty not in ["easy", "medium", "hard"]:
        return jsonify({"success": False, "message": "Invalid difficulty."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
    task = cursor.fetchone()
    if not task:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Task not found."}), 404

    points_value = None
    if points is not None:
        try:
            points_value = int(points)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Points must be a number."}), 400

    if assigned_student_ids is not None:
        valid_student_ids = _fetch_valid_student_ids(conn, assigned_student_ids)
        if len(valid_student_ids) != len(set(assigned_student_ids)):
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Invalid student list."}), 400

    deadline_value = None
    if deadline is not None:
        deadline_value = _normalize_deadline_input(deadline)
        if deadline_value is None:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Invalid deadline format."}), 400

    cursor.execute(
        """
        UPDATE tasks
        SET title = COALESCE(%s, title),
            description = COALESCE(%s, description),
            deadline = COALESCE(%s, deadline),
            points = COALESCE(%s, points),
            difficulty = COALESCE(%s, difficulty),
            updated_at = %s
        WHERE id = %s
        """,
        (
            title,
            description,
            deadline_value,
            points_value,
            difficulty,
            (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            task_id,
        ),
    )
    conn.commit()

    if assigned_student_ids is not None:
        cursor.close()
        _replace_task_assignments(conn, task_id, assigned_student_ids, teacher["id"])
        cursor = conn.cursor()

    cursor.execute(
        "SELECT deadline, points FROM tasks WHERE id = %s",
        (task_id,),
    )
    updated_task = cursor.fetchone()
    if updated_task:
        new_deadline = _parse_datetime(updated_task["deadline"])
        new_points = updated_task["points"]

        cursor.execute(
            "SELECT id, student_id, submitted_at, awarded_points FROM submissions WHERE task_id = %s",
            (task_id,),
        )
        submissions = cursor.fetchall()
        for submission in submissions:
            submitted_at = _parse_datetime(submission["submitted_at"])
            new_max = _calculate_penalty(new_points, new_deadline, submitted_at)
            awarded = submission["awarded_points"] or 0
            if awarded > new_max:
                delta = new_max - awarded
                cursor.execute(
                    "UPDATE submissions SET awarded_points = %s WHERE id = %s",
                    (new_max, submission["id"]),
                )
                cursor.execute(
                    "UPDATE users SET points = GREATEST(points + %s, 0) WHERE id = %s",
                    (delta, submission["student_id"]),
                )
        conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Task updated successfully."}), 200


@tasks_bp.route("/tasks/<int:task_id>/assignments", methods=["GET"])
def get_task_assignments(task_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT created_by FROM tasks WHERE id = %s", (task_id,))
    task = cursor.fetchone()
    if not task:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Task not found."}), 404

    cursor.execute(
        "SELECT student_id FROM task_assignments WHERE task_id = %s",
        (task_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"studentIds": [row["student_id"] for row in rows]}), 200
