from flask import Blueprint, jsonify, request

from ..services import ServiceError, ShopService, TimeProvider
from ..utils.auth import require_role, require_user

shop_bp = Blueprint("shop", __name__)


def _get_shop_service() -> ShopService:
    return ShopService(clock=TimeProvider())


@shop_bp.route("/rewards", methods=["GET"])
def list_rewards():
    user, _ = require_user()
    service = _get_shop_service()
    rewards = service.list_rewards(user)
    return jsonify({"rewards": rewards}), 200


@shop_bp.route("/rewards", methods=["POST"])
def create_reward():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    data = request.get_json() or {}
    title = data.get("title")
    description = data.get("description")
    cost = data.get("cost")

    service = _get_shop_service()
    try:
        service.create_reward(teacher, title, description, cost)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Reward created."}), 201


@shop_bp.route("/rewards/<int:reward_id>", methods=["PUT", "DELETE"])
def update_reward(reward_id: int):
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_shop_service()

    if request.method == "DELETE":
        deleted = service.delete_reward(reward_id)
        if not deleted:
            return jsonify({"success": False, "message": "Reward not found."}), 404
        return jsonify({"success": True, "message": "Reward deleted."}), 200

    data = request.get_json() or {}
    title = data.get("title")
    description = data.get("description")
    cost = data.get("cost")

    try:
        service.update_reward(reward_id, title, description, cost)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Reward updated."}), 200


@shop_bp.route("/rewards/<int:reward_id>/purchase", methods=["POST"])
def purchase_reward(reward_id: int):
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_shop_service()
    try:
        service.purchase_reward(student, reward_id)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "Purchase complete."}), 201


@shop_bp.route("/purchases/all", methods=["GET"])
def list_all_purchases():
    teacher, error = require_role("tutor")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_shop_service()
    purchases = service.list_all_purchases()
    return jsonify({"purchases": purchases}), 200


@shop_bp.route("/purchases", methods=["GET"])
def list_purchases():
    student, error = require_role("student")
    if error:
        return jsonify(error[0]), error[1]

    service = _get_shop_service()
    purchases = service.list_purchases(student["id"])
    return jsonify({"purchases": purchases}), 200
