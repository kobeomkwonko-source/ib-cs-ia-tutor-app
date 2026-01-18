from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..utils.auth import require_role, require_user

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/rewards", methods=["GET"])
def list_rewards():
    user, _ = require_user()
    conn = get_db()
    cursor = conn.cursor()
    if user and user["role"] == "tutor":
        cursor.execute(
            "SELECT id, title, description, cost, active FROM rewards ORDER BY created_at DESC"
        )
    else:
        cursor.execute(
            "SELECT id, title, description, cost, active FROM rewards WHERE active = 1 ORDER BY created_at DESC"
        )
    rewards = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"rewards": rewards}), 200


@shop_bp.route("/rewards", methods=["POST"])
def create_reward():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    cost = data.get("cost")

    if not title or cost is None:
        return jsonify({"success": False, "message": "Title and cost are required."}), 400

    try:
        cost_value = int(cost)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Cost must be a number."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO rewards (title, description, cost, created_by) VALUES (%s, %s, %s, %s)",
        (title, description, cost_value, teacher["id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Reward created."}), 201


@shop_bp.route("/rewards/<int:reward_id>", methods=["PUT", "DELETE"])
def update_reward(reward_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    if request.method == "DELETE":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rewards WHERE id = %s", (reward_id,))
        conn.commit()
        deleted = cursor.rowcount
        cursor.close()
        conn.close()

        if deleted == 0:
            return jsonify({"success": False, "message": "Reward not found."}), 404

        return jsonify({"success": True, "message": "Reward deleted."}), 200

    data = request.get_json()
    title = data.get("title")
    description = data.get("description")
    cost = data.get("cost")
    active = data.get("active")

    conn = get_db()
    cursor = conn.cursor()
    cost_value = None
    if cost is not None:
        try:
            cost_value = int(cost)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Cost must be a number."}), 400

    cursor.execute(
        """
        UPDATE rewards
        SET title = COALESCE(%s, title),
            description = COALESCE(%s, description),
            cost = COALESCE(%s, cost),
            active = COALESCE(%s, active),
            updated_at = %s
        WHERE id = %s
        """,
        (
            title,
            description,
            cost_value,
            active,
            (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
            reward_id,
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Reward updated."}), 200


@shop_bp.route("/rewards/<int:reward_id>/purchase", methods=["POST"])
def purchase_reward(reward_id: int):
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, cost FROM rewards WHERE id = %s AND active = 1",
        (reward_id,),
    )
    reward = cursor.fetchone()
    if not reward:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Reward not found."}), 404

    if student["points"] < reward["cost"]:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "too small points"}), 400

    cursor.execute(
        "INSERT INTO purchases (reward_id, student_id, cost_at_purchase) VALUES (%s, %s, %s)",
        (reward_id, student["id"], reward["cost"]),
    )
    cursor.execute(
        "UPDATE users SET points = GREATEST(points - %s, 0) WHERE id = %s",
        (reward["cost"], student["id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Purchase complete."}), 201


@shop_bp.route("/purchases/all", methods=["GET"])
def list_all_purchases():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id,
               p.purchased_at,
               p.cost_at_purchase,
               r.title,
               u.username,
               u.email
        FROM purchases p
        JOIN rewards r ON r.id = p.reward_id
        JOIN users u ON u.id = p.student_id
        ORDER BY p.purchased_at DESC
        """
    )
    purchases = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"purchases": purchases}), 200


@shop_bp.route("/purchases", methods=["GET"])
def list_purchases():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.purchased_at, p.cost_at_purchase, r.title
        FROM purchases p
        JOIN rewards r ON r.id = p.reward_id
        WHERE p.student_id = %s
        ORDER BY p.purchased_at DESC
        """,
        (student["id"],),
    )
    purchases = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"purchases": purchases}), 200
