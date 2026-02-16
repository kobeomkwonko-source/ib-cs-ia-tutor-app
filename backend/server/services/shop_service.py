from __future__ import annotations

from typing import Optional

from ..db import get_db
from ..models import Reward
from .core import ServiceError, TimeProvider


class ShopService:
    def __init__(self, clock: Optional[TimeProvider] = None):
        self.clock = clock or TimeProvider()

    def list_rewards(self, user: Optional[dict]) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, title, description, cost FROM rewards ORDER BY created_at DESC"
            )
            rewards = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return rewards

    def create_reward(self, teacher: dict, title: str, description: Optional[str], cost):
        if not title or cost is None:
            raise ServiceError("Title and cost are required.")

        try:
            cost_value = int(cost)
        except (TypeError, ValueError):
            raise ServiceError("Cost must be a number.")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO rewards (title, description, cost, created_by) VALUES (%s, %s, %s, %s)",
                (title, description, cost_value, teacher["id"]),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def update_reward(self, reward_id: int, title, description, cost) -> None:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cost_value = None
            if cost is not None:
                try:
                    cost_value = int(cost)
                except (TypeError, ValueError):
                    raise ServiceError("Cost must be a number.")

            cursor.execute(
                """
                UPDATE rewards
                SET title = COALESCE(%s, title),
                    description = COALESCE(%s, description),
                    cost = COALESCE(%s, cost),
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    title,
                    description,
                    cost_value,
                    self.clock.now_str(),
                    reward_id,
                ),
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def delete_reward(self, reward_id: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM rewards WHERE id = %s", (reward_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()

    def purchase_reward(self, student: dict, reward_id: int) -> None:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, title, description, cost FROM rewards WHERE id = %s",
                (reward_id,),
            )
            reward_row = cursor.fetchone()
            if not reward_row:
                raise ServiceError("Reward not found.", status=404)

            reward = Reward(
                id=reward_row["id"],
                title=reward_row["title"],
                description=reward_row.get("description"),
                cost=reward_row["cost"],
                created_by=0,
            )

            if student["points"] < reward.cost:
                raise ServiceError("too small points", status=400)

            points_before = int(student["points"])
            points_after = max(points_before - int(reward.cost), 0)
            purchased_at = self.clock.now_str()

            cursor.execute(
                """
                INSERT INTO purchases (reward_id, student_id, cost_at_purchase, purchased_at)
                VALUES (%s, %s, %s, %s)
                """,
                (reward_id, student["id"], reward.cost, purchased_at),
            )
            purchase_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO reward_purchase_ledger (
                    purchase_id,
                    reward_id,
                    student_id,
                    reward_title,
                    reward_description,
                    reward_cost,
                    cost_at_purchase,
                    student_username,
                    student_email,
                    points_before,
                    points_after,
                    purchased_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    purchase_id,
                    reward_id,
                    student["id"],
                    reward.title,
                    reward.description,
                    reward.cost,
                    reward.cost,
                    student["username"],
                    student.get("email"),
                    points_before,
                    points_after,
                    purchased_at,
                ),
            )
            cursor.execute(
                "UPDATE users SET points = %s WHERE id = %s",
                (points_after, student["id"]),
            )
            conn.commit()
        except ServiceError:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise ServiceError("Failed to complete purchase.", status=500) from exc
        finally:
            cursor.close()
            conn.close()

    def list_all_purchases(self) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.id,
                       l.purchased_at,
                       l.cost_at_purchase,
                       l.reward_title AS title,
                       l.student_username AS username,
                       l.student_email AS email
                FROM reward_purchase_ledger l
                ORDER BY l.purchased_at DESC
                """
            )
            purchases = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return purchases

    def list_purchases(self, student_id: int) -> list[dict]:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.id,
                       l.purchased_at,
                       l.cost_at_purchase,
                       l.reward_title AS title
                FROM reward_purchase_ledger l
                WHERE l.student_id = %s
                ORDER BY l.purchased_at DESC
                """,
                (student_id,),
            )
            purchases = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return purchases
