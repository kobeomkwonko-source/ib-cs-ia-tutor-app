import jwt
from flask import current_app, request

from ..db import get_db


def decode_token(token: str):
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET"],
        algorithms=[current_app.config["JWT_ALGORITHM"]],
    )


def get_current_user():
    token = request.cookies.get(current_app.config["JWT_COOKIE_NAME"])
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError as exc:
        print("JWT error:", type(exc).__name__, exc)
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, role, points FROM users WHERE id = %s",
        (user_id,),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def require_user():
    user = get_current_user()
    if not user:
        return None, ({"success": False, "message": "Unauthorized."}, 401)
    return user, None


def require_role(role: str):
    user, error = require_user()
    if error:
        return None, error
    if user["role"] != role:
        return None, ({"success": False, "message": "Forbidden."}, 403)
    return user, None
