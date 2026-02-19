import os
from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

# Load local env files if present.
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=False)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)


def _resolve_upload_folder():
    upload_env = os.getenv("UPLOAD_FOLDER")
    if upload_env:
        if os.path.isabs(upload_env):
            return upload_env
        return os.path.abspath(os.path.join(BASE_DIR, upload_env))
    return os.path.join(BASE_DIR, "uploads")


class Config:
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "12345678")
    DB_NAME = os.getenv("DB_NAME", "tutor_app")

    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))
    JWT_COOKIE_NAME = "access_token"
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET", "dev-refresh-secret-change-me")
    REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "7"))
    REFRESH_COOKIE_NAME = "refresh_token"
    REFRESH_COOKIE_SECURE = os.getenv("REFRESH_COOKIE_SECURE", "false").lower() == "true"
    REFRESH_COOKIE_SAMESITE = os.getenv("REFRESH_COOKIE_SAMESITE", "Lax")

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
