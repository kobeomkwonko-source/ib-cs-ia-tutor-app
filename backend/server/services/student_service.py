from __future__ import annotations

from ..db import get_db


class StudentService:
    def leaderboard(self) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
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
        finally:
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
            row["tier"] = self._assign_tier(row["rank"], total_students)

        return leaderboard_rows

    def student_progress(self, student: dict) -> dict:
        conn = get_db()
        cursor = conn.cursor()
        try:
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
        finally:
            cursor.close()
            conn.close()

        submitted_task_ids = {row["task_id"] for row in submissions}

        for task in tasks:
            task["status"] = (
                "completed" if task["id"] in submitted_task_ids else "pending"
            )

        return {"tasks": tasks, "points": student["points"]}

    def list_students(self) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, username, email, points FROM users WHERE role = 'student' ORDER BY username"
            )
            students = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return students

    def students_overview(self, teacher_id: int) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
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
                (teacher_id,),
            )
            rows = cursor.fetchall()
        finally:
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
        return overview

    def _assign_tier(self, rank: int, total: int) -> str:
        if total == 0:
            return "Bronze"
        if total <= 6:
            tiers = ["Challenger", "Master", "Diamond", "Gold", "Silver", "Bronze"]
            if 1 <= rank <= len(tiers):
                return tiers[rank - 1]
            return "Bronze"

        percentile = (rank / total) * 100.0
        if percentile <= 5:
            return "Challenger"
        if percentile <= 10:
            return "Master"
        if percentile <= 20:
            return "Diamond"
        if percentile <= 30:
            return "Gold"
        if percentile <= 50:
            return "Silver"
        return "Bronze"
