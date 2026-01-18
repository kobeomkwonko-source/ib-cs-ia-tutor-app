from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import bcrypt
from .routes.auth import auth_bp
from .routes.tasks import tasks_bp
from .routes.students import students_bp
from .routes.shop import shop_bp
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_CONTENT_LENGTH"]

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    bcrypt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(shop_bp)

    @app.get("/")
    def index():
        return "Backend is running"

    return app
