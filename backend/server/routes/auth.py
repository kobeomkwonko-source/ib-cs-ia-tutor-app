from datetime import datetime, timedelta

import jwt
from flask import Blueprint, current_app, jsonify, make_response, request

from ..db import get_db
from ..extensions import bcrypt
from ..utils.auth import get_current_user

auth_bp = Blueprint("auth", __name__)


def _generate_token(user_id: int, role: str):
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


def _get_user_by_username(username: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, password, role, points FROM users WHERE username = %s",
        (username,),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
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

    if role not in ["tutor", "student"]:
        return jsonify({"success": False, "message": "Invalid role."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Username already exists."}), 400

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    existing_email = cursor.fetchone()
    if existing_email:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Email already exists."}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    cursor.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
        (username, email, hashed_password, role),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        jsonify({"success": True, "message": "Registration successful. Please log in."}),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "wrong information"}), 401

    user = _get_user_by_username(username)
    if user is None:
        return jsonify({"success": False, "message": "wrong information"}), 401

    is_valid = bcrypt.check_password_hash(user["password"], password)
    if not is_valid:
        return jsonify({"success": False, "message": "wrong information"}), 401

    token, _ = _generate_token(user["id"], user["role"])
    response = make_response(
        jsonify(
            {
                "success": True,
                "message": "Login successful.",
                "userId": user["id"],
                "username": user["username"],
                "email": user.get("email"),
                "role": user["role"],
                "points": user["points"],
            }
        ),
        200,
    )
    response.set_cookie(
        current_app.config["JWT_COOKIE_NAME"],
        token,
        httponly=True,
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        secure=current_app.config["JWT_COOKIE_SECURE"],
        max_age=current_app.config["JWT_EXPIRES_MINUTES"] * 60,
        path="/",
    )
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
    response.set_cookie(
        current_app.config["JWT_COOKIE_NAME"],
        "",
        httponly=True,
        samesite=current_app.config["JWT_COOKIE_SAMESITE"],
        secure=current_app.config["JWT_COOKIE_SECURE"],
        max_age=0,
        path="/",
    )
    return response
