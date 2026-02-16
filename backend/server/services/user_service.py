from __future__ import annotations

from typing import Optional

from ..db import get_db
from ..models import User
from .core import ServiceError


class UserService:
    def __init__(self, bcrypt):
        self.bcrypt = bcrypt

    def get_by_username(self, username: str) -> Optional[User]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, username, email, password, role, points FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not row:
            return None

        return self._user_from_row(row)

    def get_by_id(self, user_id: int) -> Optional[User]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, username, email, role, points FROM users WHERE id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not row:
            return None

        return User(
            id=row.get("id") or 0,
            username=row.get("username") or "",
            password="",
            role=row.get("role") or "",
            email=row.get("email"),
            points=row.get("points") or 0,
        )

    def register_student(self, username: str, email: str, password: str) -> None:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing = cursor.fetchone()
            if existing:
                raise ServiceError("Username already exists.")

            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_email = cursor.fetchone()
            if existing_email:
                raise ServiceError("Email already exists.")

            hashed_password = self.bcrypt.generate_password_hash(password).decode("utf-8")
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, hashed_password, "student"),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def update_user(self, user_id: int, updates: dict) -> None:
        username = updates.get("username")
        email = updates.get("email")
        password = updates.get("password")
        points = updates.get("points")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            existing_user = cursor.fetchone()
            if not existing_user:
                raise ServiceError("User not found.", status=404)

            set_clauses = []
            params = []

            if username:
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (username, user_id),
                )
                if cursor.fetchone():
                    raise ServiceError("Username already exists.")
                set_clauses.append("username = %s")
                params.append(username)

            if email is not None:
                normalized_email = email or None
                if normalized_email is not None:
                    cursor.execute(
                        "SELECT id FROM users WHERE email = %s AND id != %s",
                        (normalized_email, user_id),
                    )
                    if cursor.fetchone():
                        raise ServiceError("Email already exists.")
                set_clauses.append("email = %s")
                params.append(normalized_email)

            if password:
                hashed_password = self.bcrypt.generate_password_hash(password).decode("utf-8")
                set_clauses.append("password = %s")
                params.append(hashed_password)

            if points is not None:
                try:
                    points_value = int(points)
                except (TypeError, ValueError):
                    raise ServiceError("Points must be an integer.")
                if points_value < 0:
                    raise ServiceError("Points must be non-negative.")
                set_clauses.append("points = %s")
                params.append(points_value)

            if not set_clauses:
                raise ServiceError("No updates provided.")

            params.append(user_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s",
                tuple(params),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def delete_user(self, user_id: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def _user_from_row(self, row: dict) -> User:
        return User(
            id=row.get("id") or 0,
            username=row.get("username") or "",
            password=row.get("password") or "",
            role=row.get("role") or "",
            email=row.get("email"),
            points=row.get("points") or 0,
        )
