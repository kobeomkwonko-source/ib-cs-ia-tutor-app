from __future__ import annotations

import math
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

from ..models import Task


class ServiceError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class DateTimeParser:
    def parse(self, value) -> datetime:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValueError("Unsupported datetime type")

        normalized = value.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
        ):
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue

        try:
            return (
                datetime.fromisoformat(normalized.replace("Z", "+00:00"))
                .replace(tzinfo=None)
            )
        except ValueError:
            pass

        try:
            return parsedate_to_datetime(normalized).replace(tzinfo=None)
        except Exception as exc:
            raise ValueError(f"Invalid datetime format: {value}") from exc

    def normalize_input(self, value) -> Optional[str]:
        if value is None:
            return None
        try:
            parsed = self.parse(value)
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    def format_iso(self, value) -> Optional[str]:
        if value is None:
            return None
        try:
            parsed = self.parse(value)
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")


class TimeProvider:
    def __init__(self, offset_hours: int = 9):
        self.offset_hours = offset_hours

    def now(self) -> datetime:
        return datetime.utcnow() + timedelta(hours=self.offset_hours)

    def now_str(self, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return self.now().strftime(fmt)


class LatePenaltyPolicy:
    def __init__(self, decay: float = 0.5, max_days: int = 7):
        self.decay = decay
        self.max_days = max_days

    def evaluate(self, task: Task, submitted_at: datetime) -> tuple[int, int]:
        deadline = task.deadline
        if deadline is None:
            return task.points, 0
        if submitted_at <= deadline:
            return task.points, 0
        seconds_late = (submitted_at - deadline).total_seconds()
        days_late = math.ceil(seconds_late / 86400)
        if days_late >= self.max_days:
            return 0, days_late
        penalized = int(task.points * (self.decay ** days_late))
        return max(0, penalized), days_late
