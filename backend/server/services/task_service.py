from __future__ import annotations

import json
import os
from typing import Iterable, Optional

from werkzeug.datastructures import FileStorage

from ..db import get_db
from ..models import Task, Submission
from ..utils.files import generate_pdf_storage_name
from .core import DateTimeParser, LatePenaltyPolicy, ServiceError, TimeProvider


class TaskService:
    def __init__(
        self,
        upload_folder: str,
        parser: Optional[DateTimeParser] = None,
        clock: Optional[TimeProvider] = None,
        penalty_policy: Optional[LatePenaltyPolicy] = None,
    ):
        self.upload_folder = upload_folder
        self.parser = parser or DateTimeParser()
        self.clock = clock or TimeProvider()
        self.penalty_policy = penalty_policy or LatePenaltyPolicy()

    def list_tasks(self, user: dict) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        tasks: list[dict] = []
        try:
            if user["role"] == "student":
                cursor.execute(
                    """
                    SELECT t.id, t.title, t.description, t.deadline, t.points, t.created_by, t.pdf_path
                    FROM tasks t
                    JOIN task_assignments a ON a.task_id = t.id
                    WHERE a.student_id = %s
                    ORDER BY t.deadline IS NULL, t.deadline
                    """,
                    (user["id"],),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    "SELECT DISTINCT task_id FROM submissions WHERE student_id = %s",
                    (user["id"],),
                )
                submitted = {row["task_id"] for row in cursor.fetchall()}
            else:
                cursor.execute(
                    "SELECT id, title, description, deadline, points, created_by, pdf_path FROM tasks ORDER BY deadline IS NULL, deadline"
                )
                rows = cursor.fetchall()
                submitted = set()

            for row in rows:
                task = self._task_from_row(row)
                task_data = self._task_to_dict(task)
                task_data["is_done"] = task.id in submitted
                tasks.append(task_data)
        finally:
            cursor.close()
            conn.close()

        return tasks

    def create_task(
        self,
        teacher: dict,
        data: dict,
        pdf: Optional[FileStorage],
    ) -> None:
        title = data.get("title")
        description = data.get("description")
        deadline = data.get("deadline")
        points = data.get("points")
        assigned_student_ids = self._normalize_student_ids(
            self._parse_assigned_student_ids(data.get("assignedStudentIds"))
        )

        if not title:
            raise ServiceError("Title is required.")
        if not description:
            raise ServiceError("Description is required.")
        if not deadline:
            raise ServiceError("Deadline is required.")
        if points is None:
            raise ServiceError("Points are required.")
        if assigned_student_ids is None or len(assigned_student_ids) == 0:
            raise ServiceError("Select at least one student.")

        try:
            points_value = int(points)
        except (TypeError, ValueError):
            raise ServiceError("Points must be a number.")

        deadline_value = self.parser.normalize_input(deadline)
        if not deadline_value:
            raise ServiceError("Invalid deadline format.")

        conn = get_db()
        cursor = conn.cursor()
        try:
            valid_student_ids = self._fetch_valid_student_ids(conn, assigned_student_ids)
            if len(valid_student_ids) != len(set(assigned_student_ids)):
                raise ServiceError("Invalid student list.")

            pdf_path = None
            if pdf:
                filename = pdf.filename or ""
                if not filename.lower().endswith(".pdf"):
                    raise ServiceError("Only PDF uploads are allowed.")
                storage_name = generate_pdf_storage_name(filename)
                storage_path = os.path.join(self.upload_folder, storage_name)
                pdf.save(storage_path)
                pdf_path = storage_name

            cursor.execute(
                """
                INSERT INTO tasks (title, description, deadline, points, created_by, pdf_path)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (title, description, deadline_value, points_value, teacher["id"], pdf_path),
            )
            conn.commit()
            task_id = cursor.lastrowid
        finally:
            cursor.close()

        self._replace_task_assignments(conn, task_id, assigned_student_ids, teacher["id"])
        conn.close()

    def delete_task(self, task_id: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def update_task(self, task_id: int, data: dict, teacher: dict) -> None:
        title = data.get("title")
        description = data.get("description")
        deadline = data.get("deadline")
        points = data.get("points")
        assigned_student_ids = None
        if "assignedStudentIds" in data:
            assigned_student_ids = self._normalize_student_ids(data.get("assignedStudentIds"))
            if assigned_student_ids is None or len(assigned_student_ids) == 0:
                raise ServiceError("Select at least one student.")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
            task_row = cursor.fetchone()
            if not task_row:
                raise ServiceError("Task not found.", status=404)

            points_value = None
            if points is not None:
                try:
                    points_value = int(points)
                except (TypeError, ValueError):
                    raise ServiceError("Points must be a number.")

            if assigned_student_ids is not None:
                valid_student_ids = self._fetch_valid_student_ids(conn, assigned_student_ids)
                if len(valid_student_ids) != len(set(assigned_student_ids)):
                    raise ServiceError("Invalid student list.")

            deadline_value = None
            if deadline is not None:
                deadline_value = self.parser.normalize_input(deadline)
                if deadline_value is None:
                    raise ServiceError("Invalid deadline format.")

            cursor.execute(
                """
                UPDATE tasks
                SET title = COALESCE(%s, title),
                    description = COALESCE(%s, description),
                    deadline = COALESCE(%s, deadline),
                    points = COALESCE(%s, points),
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    title,
                    description,
                    deadline_value,
                    points_value,
                    self.clock.now_str(),
                    task_id,
                ),
            )
            conn.commit()

            if assigned_student_ids is not None:
                cursor.close()
                self._replace_task_assignments(
                    conn, task_id, assigned_student_ids, teacher["id"]
                )
                cursor = conn.cursor()

            cursor.execute(
                "SELECT deadline, points FROM tasks WHERE id = %s",
                (task_id,),
            )
            updated_task_row = cursor.fetchone()
            if updated_task_row:
                updated_task = self._task_from_row(updated_task_row)
                cursor.execute(
                    "SELECT id, student_id, submitted_at, awarded_points FROM submissions WHERE task_id = %s",
                    (task_id,),
                )
                submissions = cursor.fetchall()
                for submission_row in submissions:
                    submission = self._submission_from_row(submission_row)
                    new_max, _ = self.penalty_policy.evaluate(
                        updated_task, submission.submitted_at
                    )
                    awarded = submission.awarded_points or 0
                    if awarded > new_max:
                        delta = new_max - awarded
                        cursor.execute(
                            "UPDATE submissions SET awarded_points = %s WHERE id = %s",
                            (new_max, submission.id),
                        )
                        cursor.execute(
                            "UPDATE users SET points = GREATEST(points + %s, 0) WHERE id = %s",
                            (delta, submission.student_id),
                        )
                conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_task_assignments(self, task_id: int) -> list[int]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT created_by FROM tasks WHERE id = %s", (task_id,))
            task = cursor.fetchone()
            if not task:
                raise ServiceError("Task not found.", status=404)

            cursor.execute(
                "SELECT student_id FROM task_assignments WHERE task_id = %s",
                (task_id,),
            )
            rows = cursor.fetchall()
            return [row["student_id"] for row in rows]
        finally:
            cursor.close()
            conn.close()

    def resolve_task_file_path(self, task_id: int, user: dict) -> str:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT pdf_path FROM tasks WHERE id = %s", (task_id,))
            task = cursor.fetchone()
            if not task:
                raise ServiceError("Task not found.", status=404)

            if user["role"] == "student":
                cursor.execute(
                    "SELECT 1 FROM task_assignments WHERE task_id = %s AND student_id = %s",
                    (task_id, user["id"]),
                )
                assignment = cursor.fetchone()
                if not assignment:
                    raise ServiceError("Task not assigned.", status=403)

            resolved_path = self._resolve_task_pdf_path(task.get("pdf_path"))
            if not resolved_path:
                raise ServiceError("File not found.", status=404)
            return resolved_path
        finally:
            cursor.close()
            conn.close()

    def _task_from_row(self, row: dict) -> Task:
        deadline_value = row.get("deadline")
        try:
            deadline = self.parser.parse(deadline_value) if deadline_value else None
        except ValueError:
            deadline = None
        return Task(
            id=row.get("id") or 0,
            title=row.get("title") or "",
            description=row.get("description") or "",
            deadline=deadline,
            points=row.get("points", 0) or 0,
            created_by=row.get("created_by"),
            pdf_path=row.get("pdf_path"),
        )

    def _task_to_dict(self, task: Task) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline": self.parser.format_iso(task.deadline),
            "points": task.points,
            "created_by": task.created_by,
            "pdf_path": task.pdf_path,
        }

    def _submission_from_row(self, row: dict) -> Submission:
        submitted_at_value = row.get("submitted_at")
        try:
            submitted_at = self.parser.parse(submitted_at_value) if submitted_at_value else None
        except ValueError:
            submitted_at = self.clock.now()
        return Submission(
            id=row.get("id") or 0,
            task_id=row.get("task_id") or 0,
            student_id=row.get("student_id") or 0,
            submitted_at=submitted_at,
            awarded_points=row.get("awarded_points"),
        )

    def _normalize_student_ids(self, value: Optional[Iterable]) -> Optional[list[int]]:
        if value is None:
            return None
        if not isinstance(value, list):
            return None
        normalized: list[int] = []
        for entry in value:
            try:
                normalized.append(int(entry))
            except (TypeError, ValueError):
                return None
        return normalized

    def _parse_assigned_student_ids(self, raw_value):
        if raw_value is None:
            return None
        if isinstance(raw_value, list):
            return raw_value
        if isinstance(raw_value, str):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return None
        return None

    def _fetch_valid_student_ids(self, conn, student_ids: list[int]) -> set[int]:
        if not student_ids:
            return set()
        placeholders = ", ".join(["%s"] * len(student_ids))
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id FROM users WHERE role = 'student' AND id IN ({placeholders})",
            student_ids,
        )
        rows = cursor.fetchall()
        cursor.close()
        return {row["id"] for row in rows}

    def _replace_task_assignments(
        self, conn, task_id: int, student_ids: list[int], teacher_id: int
    ) -> None:
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

    def _resolve_task_pdf_path(self, pdf_path: Optional[str]) -> Optional[str]:
        if not pdf_path:
            return None
        candidates = []
        if os.path.isabs(pdf_path):
            candidates.append(pdf_path)
        candidates.append(os.path.abspath(pdf_path))
        basename = os.path.basename(pdf_path)
        if basename:
            candidates.append(os.path.join(self.upload_folder, basename))
            candidates.append(os.path.abspath(os.path.join(self.upload_folder, basename)))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None
