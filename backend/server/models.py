from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    password: str
    role: str  # "student" or "tutor"
    email: Optional[str] = None
    points: int = 0

    tasks_created: list[Task] = field(default_factory=list, repr=False)
    submissions: list[Submission] = field(default_factory=list, repr=False)
    rewards_created: list[Reward] = field(default_factory=list, repr=False)
    purchases: list[Purchase] = field(default_factory=list, repr=False)


@dataclass
class Task:
    id: int
    title: str
    description: str
    deadline: datetime
    created_at: datetime = field(default_factory=datetime.now)
    pdf_path: Optional[str] = None
    points: int = 0
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    creator: Optional[User] = field(default=None, repr=False)
    assignments: list[TaskAssignment] = field(default_factory=list, repr=False)
    submissions: list[Submission] = field(default_factory=list, repr=False)
    reminders: list[ReminderLog] = field(default_factory=list, repr=False)


@dataclass
class Submission:
    id: int
    task_id: int
    student_id: int
    submitted_at: datetime
    text_content: Optional[str] = None
    pdf_path: Optional[str] = None
    teacher_comment: Optional[str] = None
    awarded_points: Optional[int] = None
    awarded_at: Optional[datetime] = None

    task: Optional[Task] = field(default=None, repr=False)
    student: Optional[User] = field(default=None, repr=False)


@dataclass
class TaskAssignment:
    id: int
    task_id: int
    student_id: int
    assigned_by: int
    assigned_at: datetime

    task: Optional[Task] = field(default=None, repr=False)
    student: Optional[User] = field(default=None, repr=False)
    teacher: Optional[User] = field(default=None, repr=False)


@dataclass
class ReminderLog:
    id: int
    task_id: int
    student_id: int
    reminder_type: str  # "24h" or "12h"
    sent_at: datetime

    task: Optional[Task] = field(default=None, repr=False)
    student: Optional[User] = field(default=None, repr=False)


@dataclass
class Reward:
    id: int
    title: str
    created_by: int
    description: Optional[str] = None
    cost: int = 0
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    creator: Optional[User] = field(default=None, repr=False)
    purchases: list[Purchase] = field(default_factory=list, repr=False)
    ledger_entries: list[RewardPurchaseLedger] = field(default_factory=list, repr=False)


@dataclass
class Purchase:
    id: int
    purchased_at: datetime
    cost_at_purchase: int
    reward_id: Optional[int] = None
    student_id: Optional[int] = None

    reward: Optional[Reward] = field(default=None, repr=False)
    student: Optional[User] = field(default=None, repr=False)
    ledger_entry: Optional[RewardPurchaseLedger] = field(default=None, repr=False)


@dataclass
class RewardPurchaseLedger:
    id: int
    reward_title: str
    reward_cost: int
    cost_at_purchase: int
    student_username: str
    points_before: int
    points_after: int
    purchased_at: datetime
    created_at: datetime
    purchase_id: Optional[int] = None
    reward_id: Optional[int] = None
    student_id: Optional[int] = None
    reward_description: Optional[str] = None
    student_email: Optional[str] = None

    purchase: Optional[Purchase] = field(default=None, repr=False)
    reward: Optional[Reward] = field(default=None, repr=False)
    student: Optional[User] = field(default=None, repr=False)


@dataclass
class RefreshToken:
    id: int
    user_id: int
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[str] = None
    created_by_ip: Optional[str] = None
    created_by_user_agent: Optional[str] = None
