from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Optional

import jwt
from flask import Blueprint, current_app, jsonify, make_response, request

from ..db import get_db
from ..extensions import bcrypt
from ..services import ServiceError, UserService
from ..utils.auth import get_current_user, require_user

auth_bp = Blueprint("auth", __name__)


def _generate_access_token(user_id: int, role: str):
    expires_at = datetime.utcnow() + timedelta(
        minutes=current_app.config["JWT_EXPIRES_MINUTES"]
    )
    payload = {"sub": str(user_id), "role": role, "exp": expires_at}
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
    return token, expires_at


def _get_user_service() -> UserService:
    return UserService(bcrypt)


def _hash_refresh_token(token: str) -> str:
    secret = current_app.config["REFRESH_TOKEN_SECRET"]
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _store_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> None:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_by_ip, created_by_user_agent)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                token_hash,
                expires_at,
                request.remote_addr,
                request.headers.get("User-Agent"),
            ),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _issue_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(
        days=current_app.config["REFRESH_TOKEN_EXPIRES_DAYS"]
    )
    _store_refresh_token(user_id, token_hash, expires_at)
    return raw_token, token_hash, expires_at


def _get_refresh_token_record(token_hash: str) -> Optional[dict]:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM refresh_tokens WHERE token_hash = %s", (token_hash,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def _revoke_refresh_token(token_hash: str, replaced_by_hash: Optional[str] = None) -> None:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = %s, replaced_by = %s
            WHERE token_hash = %s AND revoked_at IS NULL
            """,
            (datetime.utcnow(), replaced_by_hash, token_hash),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _revoke_all_user_tokens(user_id: int) -> None:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE refresh_tokens SET revoked_at = %s WHERE user_id = %s AND revoked_at IS NULL",
            (datetime.utcnow(), user_id),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _set_access_cookie(response, token: str) -> None:
    response.set_cookie(
        current_app.config["JWT_COOKIE_NAME"],
        token,
        httponly=True,
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        secure=current_app.config["JWT_COOKIE_SECURE"],
        max_age=current_app.config["JWT_EXPIRES_MINUTES"] * 60,
        path="/",
    )


def _set_refresh_cookie(response, token: str) -> None:
    response.set_cookie(
        current_app.config["REFRESH_COOKIE_NAME"],
        token,
        httponly=True,
        samesite=current_app.config["REFRESH_COOKIE_SAMESITE"],
        secure=current_app.config["REFRESH_COOKIE_SECURE"],
        max_age=current_app.config["REFRESH_TOKEN_EXPIRES_DAYS"] * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response) -> None:
    response.set_cookie(
        current_app.config["JWT_COOKIE_NAME"],
        "",
        httponly=True,
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        secure=current_app.config["JWT_COOKIE_SECURE"],
        max_age=0,
        path="/",
    )
    response.set_cookie(
        current_app.config["REFRESH_COOKIE_NAME"],
        "",
        httponly=True,
        samesite=current_app.config["REFRESH_COOKIE_SAMESITE"],
        secure=current_app.config["REFRESH_COOKIE_SECURE"],
        max_age=0,
        path="/",
    )


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not username or not email or not password or not role:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Username, email, password and role are required.",
                }
            ),
            400,
        )

    if role == "teacher":
        role = "tutor"

    if role == "tutor":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Tutor accounts cannot be created.",
                }
            ),
            403,
        )

    if role != "student":
        return jsonify({"success": False, "message": "Invalid role."}), 400

    service = _get_user_service()
    try:
        service.register_student(username, email, password)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return (
        jsonify({"success": True, "message": "Registration successful. Please log in."}),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "wrong information"}), 401

    service = _get_user_service()
    user = service.get_by_username(username)
    if user is None:
        return jsonify({"success": False, "message": "wrong information"}), 401

    is_valid = bcrypt.check_password_hash(user.password, password)
    if not is_valid:
        return jsonify({"success": False, "message": "wrong information"}), 401

    access_token, _ = _generate_access_token(user.id, user.role)
    refresh_token, _, _ = _issue_refresh_token(user.id)
    response = make_response(
        jsonify(
            {
                "success": True,
                "message": "Login successful.",
                "userId": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "points": user.points,
            }
        ),
        200,
    )
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)
    return response


@auth_bp.route("/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Unauthorized."}), 401

    return (
        jsonify(
            {
                "success": True,
                "userId": user["id"],
                "username": user["username"],
                "email": user.get("email"),
                "role": user["role"],
                "points": user["points"],
            }
        ),
        200,
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"success": True, "message": "Logged out."}), 200)
    refresh_token = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    user = get_current_user()
    if user:
        _revoke_all_user_tokens(user["id"])
    if refresh_token:
        _revoke_refresh_token(_hash_refresh_token(refresh_token))
    _clear_auth_cookies(response)
    return response


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    refresh_token = request.cookies.get(current_app.config["REFRESH_COOKIE_NAME"])
    if not refresh_token:
        response = make_response(
            jsonify({"success": False, "message": "Refresh token missing."}), 401
        )
        _clear_auth_cookies(response)
        return response

    token_hash = _hash_refresh_token(refresh_token)
    record = _get_refresh_token_record(token_hash)
    if not record:
        response = make_response(
            jsonify({"success": False, "message": "Refresh token invalid."}), 401
        )
        _clear_auth_cookies(response)
        return response

    if record.get("revoked_at") is not None:
        _revoke_all_user_tokens(record["user_id"])
        response = make_response(
            jsonify({"success": False, "message": "Refresh token revoked."}), 401
        )
        _clear_auth_cookies(response)
        return response

    if record.get("expires_at") and record["expires_at"] < datetime.utcnow():
        _revoke_refresh_token(token_hash)
        response = make_response(
            jsonify({"success": False, "message": "Refresh token expired."}), 401
        )
        _clear_auth_cookies(response)
        return response

    service = _get_user_service()
    user = service.get_by_id(record["user_id"])
    if not user:
        _revoke_all_user_tokens(record["user_id"])
        response = make_response(
            jsonify({"success": False, "message": "User not found."}), 401
        )
        _clear_auth_cookies(response)
        return response

    new_refresh_token, new_hash, _ = _issue_refresh_token(user.id)
    _revoke_refresh_token(token_hash, new_hash)

    access_token, _ = _generate_access_token(user.id, user.role)
    response = make_response(jsonify({"success": True, "message": "Token refreshed."}), 200)
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, new_refresh_token)
    return response


@auth_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id: int):
    actor, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    if actor["role"] != "tutor" and actor["id"] != user_id:
        return jsonify({"success": False, "message": "Forbidden."}), 403

    data = request.get_json() or {}

    if actor["role"] != "tutor" and data.get("points") is not None:
        return jsonify({"success": False, "message": "Forbidden."}), 403

    service = _get_user_service()
    try:
        service.update_user(user_id, data)
    except ServiceError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({"success": True, "message": "User updated."}), 200


@auth_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    actor, error = require_user()
    if error:
        return jsonify(error[0]), error[1]

    if actor["role"] != "tutor" and actor["id"] != user_id:
        return jsonify({"success": False, "message": "Forbidden."}), 403

    service = _get_user_service()
    target = service.get_by_id(user_id)
    if not target:
        return jsonify({"success": False, "message": "User not found."}), 404

    if target.role == "tutor" and actor["id"] != user_id:
        return jsonify({"success": False, "message": "Cannot delete tutor accounts."}), 403

    deleted = service.delete_user(user_id)
    if not deleted:
        return jsonify({"success": False, "message": "User not found."}), 404

    response = jsonify({"success": True, "message": "User deleted."})
    if actor["id"] == user_id:
        response = make_response(response, 200)
        _revoke_all_user_tokens(user_id)
        _clear_auth_cookies(response)
        return response

    return response, 200
