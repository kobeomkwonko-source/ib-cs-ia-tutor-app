from __future__ import annotations

import os
from typing import Optional

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ..db import get_db
from ..models import Submission, Task
from ..utils.files import generate_pdf_storage_name
from .core import DateTimeParser, LatePenaltyPolicy, ServiceError, TimeProvider


class SubmissionService:
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

    def create_submission(
        self,
        student: dict,
        task_id: Optional[str],
        text_content: Optional[str],
        pdf: Optional[FileStorage],
    ) -> dict:
        if not task_id:
            raise ServiceError("taskId is required.")

        if not text_content and not pdf:
            raise ServiceError("Submission text or PDF is required.")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM task_assignments WHERE task_id = %s AND student_id = %s",
                (task_id, student["id"]),
            )
            assignment = cursor.fetchone()
            if not assignment:
                raise ServiceError("Task not assigned.", status=403)

            cursor.execute(
                "SELECT id, deadline, points FROM tasks WHERE id = %s",
                (task_id,),
            )
            task_row = cursor.fetchone()
            if not task_row:
                raise ServiceError("Task not found.", status=404)

            task = self._task_from_row(task_row)

            pdf_path = None
            if pdf:
                filename = secure_filename(pdf.filename or "")
                if not filename.lower().endswith(".pdf"):
                    raise ServiceError("Only PDF uploads are allowed.")
                storage_name = generate_pdf_storage_name(filename)
                storage_path = os.path.join(self.upload_folder, storage_name)
                pdf.save(storage_path)
                pdf_path = storage_name

            submitted_at = self.clock.now_str()
            submitted_value = self._parse_datetime_safe(submitted_at)
            max_points, days_late = self.penalty_policy.evaluate(task, submitted_value)

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
        finally:
            cursor.close()
            conn.close()

        return {
            "submissionId": submission_id,
            "maxPoints": max_points,
            "daysLate": days_late,
        }

    def list_my_submissions(self, student: dict, task_id: Optional[str]) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
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
                task = self._task_from_row(row)
                submission = self._submission_from_row(row)
                max_points, days_late = self.penalty_policy.evaluate(
                    task, submission.submitted_at
                )
                row["max_points"] = max_points
                row["days_late"] = days_late
            self._add_attempt_numbers(submissions)
            return submissions
        finally:
            cursor.close()
            conn.close()

    def list_task_submissions(self, task_id: int) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
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
                task = self._task_from_row(row)
                submission = self._submission_from_row(row)
                max_points, days_late = self.penalty_policy.evaluate(
                    task, submission.submitted_at
                )
                row["max_points"] = max_points
                row["days_late"] = days_late
            self._add_attempt_numbers(submissions)
            return submissions
        finally:
            cursor.close()
            conn.close()

    def award_submission(
        self,
        teacher: dict,
        submission_id: int,
        awarded_points: Optional[int],
        teacher_comment: Optional[str],
    ) -> None:
        if awarded_points is None:
            raise ServiceError("awardedPoints is required.")

        if awarded_points < 0:
            raise ServiceError("awardedPoints must be non-negative.")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT s.id, s.task_id, s.student_id, s.awarded_points, s.submitted_at, t.points, t.deadline
                FROM submissions s
                JOIN tasks t ON t.id = s.task_id
                WHERE s.id = %s
                """,
                (submission_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ServiceError("Submission not found.", status=404)

            task = self._task_from_row(row)
            submission = self._submission_from_row(row)
            max_points, _ = self.penalty_policy.evaluate(task, submission.submitted_at)

            if awarded_points > max_points:
                raise ServiceError("Points exceed penalty-adjusted max.")

            cursor.execute(
                """
                SELECT id, awarded_points
                FROM submissions
                WHERE task_id = %s AND student_id = %s AND awarded_points IS NOT NULL AND id != %s
                LIMIT 1
                """,
                (submission.task_id, submission.student_id, submission_id),
            )
            other_awarded = cursor.fetchone()

            previous_points = submission.awarded_points or 0
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
                    (other_awarded["awarded_points"] or 0, submission.student_id),
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
                    self.clock.now_str(),
                    submission_id,
                ),
            )
            cursor.execute(
                "UPDATE users SET points = GREATEST(points + %s, 0) WHERE id = %s",
                (delta, submission.student_id),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def award_task_submissions(
        self,
        task_id: int,
        student_id: int,
        awarded_points: Optional[int],
        teacher_comment: Optional[str],
    ) -> None:
        if awarded_points is None:
            raise ServiceError("awardedPoints is required.")

        if awarded_points < 0:
            raise ServiceError("awardedPoints must be non-negative.")

        conn = get_db()
        cursor = conn.cursor()
        try:
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
                raise ServiceError("Submissions not found.", status=404)

            latest = submissions[0]
            task = self._task_from_row(latest)
            submission = self._submission_from_row(latest)
            max_points, _ = self.penalty_policy.evaluate(task, submission.submitted_at)

            if awarded_points > max_points:
                raise ServiceError("Points exceed penalty-adjusted max.")

            previous_points = 0
            for row in submissions:
                if row["awarded_points"] is not None:
                    previous_points = row["awarded_points"] or 0
                    break

            delta = awarded_points - previous_points
            awarded_at = self.clock.now_str()
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
        finally:
            cursor.close()
            conn.close()

    def resolve_submission_file_path(self, user: dict, submission_id: int) -> str:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT pdf_path, student_id FROM submissions WHERE id = %s",
                (submission_id,),
            )
            submission = cursor.fetchone()
            if not submission or not submission["pdf_path"]:
                raise ServiceError("File not found.", status=404)

            resolved_path = self._resolve_pdf_path(submission["pdf_path"])
            if not resolved_path:
                raise ServiceError("File not found.", status=404)

            if user["role"] == "student" and submission["student_id"] != user["id"]:
                raise ServiceError("Forbidden.", status=403)

            return resolved_path
        finally:
            cursor.close()
            conn.close()

    def delete_submission(self, user: dict, submission_id: int) -> None:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, task_id, student_id, awarded_points, pdf_path
                FROM submissions
                WHERE id = %s
                """,
                (submission_id,),
            )
            submission = cursor.fetchone()
            if not submission:
                raise ServiceError("Submission not found.", status=404)

            if user["role"] == "student" and submission["student_id"] != user["id"]:
                raise ServiceError("Forbidden.", status=403)

            if user["role"] == "student" and submission["awarded_points"] is not None:
                raise ServiceError("Awarded submissions cannot be deleted.", status=403)

            resolved_path = self._resolve_pdf_path(submission.get("pdf_path"))

            if submission["awarded_points"] is not None:
                cursor.execute(
                    """
                    SELECT MAX(awarded_points) AS max_points
                    FROM submissions
                    WHERE task_id = %s AND student_id = %s AND awarded_points IS NOT NULL
                    """,
                    (submission["task_id"], submission["student_id"]),
                )
                old_effective = cursor.fetchone()["max_points"] or 0
                cursor.execute(
                    """
                    SELECT MAX(awarded_points) AS max_points
                    FROM submissions
                    WHERE task_id = %s AND student_id = %s AND id != %s AND awarded_points IS NOT NULL
                    """,
                    (submission["task_id"], submission["student_id"], submission_id),
                )
                new_effective = cursor.fetchone()["max_points"] or 0
                delta = new_effective - old_effective
                if delta != 0:
                    cursor.execute(
                        "UPDATE users SET points = GREATEST(points + %s, 0) WHERE id = %s",
                        (delta, submission["student_id"]),
                    )

            cursor.execute("DELETE FROM submissions WHERE id = %s", (submission_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        if resolved_path:
            try:
                os.remove(resolved_path)
            except OSError:
                pass

    def _task_from_row(self, row: dict) -> Task:
        deadline_value = row.get("deadline")
        try:
            deadline = self.parser.parse(deadline_value) if deadline_value else None
        except ValueError:
            deadline = None
        points = row.get("points", 0) or 0
        return Task(
            id=row.get("task_id") or row.get("id") or 0,
            title=row.get("title") or "",
            description=row.get("description") or "",
            deadline=deadline,
            points=points,
            created_by=row.get("created_by"),
            pdf_path=row.get("pdf_path"),
        )

    def _submission_from_row(self, row: dict) -> Submission:
        submitted_at_value = row.get("submitted_at")
        submitted_at = self._parse_datetime_safe(submitted_at_value)
        return Submission(
            id=row.get("id") or 0,
            task_id=row.get("task_id") or 0,
            student_id=row.get("student_id") or 0,
            submitted_at=submitted_at,
            text_content=row.get("text_content"),
            pdf_path=row.get("pdf_path"),
            teacher_comment=row.get("teacher_comment"),
            awarded_points=row.get("awarded_points"),
            awarded_at=row.get("awarded_at"),
        )

    def _parse_datetime_safe(self, value):
        if not value:
            return self.clock.now()
        try:
            return self.parser.parse(value)
        except ValueError:
            return self.clock.now()

    def _add_attempt_numbers(self, submissions, key: str = "student_id") -> None:
        counts = {}
        for row in submissions:
            student_id = row.get(key)
            if student_id is None:
                continue
            counts[student_id] = counts.get(student_id, 0) + 1
            row["attempt_number"] = counts[student_id]

    def _resolve_pdf_path(self, pdf_path: Optional[str]) -> Optional[str]:
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
