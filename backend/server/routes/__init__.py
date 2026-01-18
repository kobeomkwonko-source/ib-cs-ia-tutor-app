from .auth import auth_bp
from .tasks import tasks_bp
from .students import students_bp
from .shop import shop_bp

__all__ = ["auth_bp", "tasks_bp", "students_bp", "shop_bp"]
