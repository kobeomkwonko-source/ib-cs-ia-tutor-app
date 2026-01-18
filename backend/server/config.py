import os


def _resolve_upload_folder():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    upload_env = os.getenv("UPLOAD_FOLDER")
    if upload_env:
        if os.path.isabs(upload_env):
            return upload_env
        return os.path.abspath(os.path.join(base_dir, upload_env))
    return os.path.join(base_dir, "uploads")


class Config:
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "12345678")
    DB_NAME = os.getenv("DB_NAME", "tutor_app")

    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))
    JWT_COOKIE_NAME = "access_token"
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")

    CORS_ORIGINS = ["http://127.0.0.1:5173"]

    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))

    UPLOAD_FOLDER = _resolve_upload_folder()
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_SENDER = os.getenv("SMTP_SENDER", SMTP_USER)

    KST_OFFSET_HOURS = 9
