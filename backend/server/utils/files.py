import os
import secrets

from werkzeug.utils import secure_filename


def generate_pdf_storage_name(original_filename: str) -> str:
    filename = secure_filename(original_filename or "")
    _, ext = os.path.splitext(filename)
    ext = (ext or ".pdf").lower()
    return f"{secrets.token_hex(16)}{ext}"
