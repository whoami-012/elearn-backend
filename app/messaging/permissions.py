import logging
from enum import Enum

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.exceptions import forbidden
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    FACULTY = "faculty"
    ADMIN = "admin"


ALLOWED_MESSAGE_PAIRS = {
    ("student", "teacher"),
    ("teacher", "student"),
    ("student", "faculty"),
    ("faculty", "student"),
    ("teacher", "faculty"),
    ("faculty", "teacher"),
}


def normalized_role(role: str | Enum) -> str:
    value = role.value if isinstance(role, Enum) else str(role)
    return value.lower()


def can_users_message(sender_role: str | Enum, receiver_role: str | Enum) -> bool:
    return (normalized_role(sender_role), normalized_role(receiver_role)) in ALLOWED_MESSAGE_PAIRS


def validate_role_pair(sender: User, receiver: User) -> None:
    if not can_users_message(sender.role, receiver.role):
        logger.warning(
            "messaging_role_pair_denied sender_id=%s receiver_id=%s sender_role=%s receiver_role=%s",
            sender.id,
            receiver.id,
            normalized_role(sender.role),
            normalized_role(receiver.role),
        )
        raise forbidden("ROLE_PAIR_NOT_ALLOWED", "These user roles are not allowed to message each other.")


async def _student_is_enrolled_with_instructor(
    db: AsyncSession, student_id, instructor_id
) -> bool:
    statement = select(
        exists().where(
            Enrollment.user_id == student_id,
            Enrollment.is_active.is_(True),
            Course.id == Enrollment.course_id,
            Course.faculty_id == instructor_id,
            Course.is_deleted.is_(False),
        )
    )
    return bool(await db.scalar(statement))


async def validate_academic_relationship(db: AsyncSession, sender: User, receiver: User) -> None:
    sender_role = normalized_role(sender.role)
    receiver_role = normalized_role(receiver.role)
    allowed = False

    if sender_role == "student" and receiver_role in {"teacher", "faculty"}:
        allowed = await _student_is_enrolled_with_instructor(db, sender.id, receiver.id)
    elif receiver_role == "student" and sender_role in {"teacher", "faculty"}:
        allowed = await _student_is_enrolled_with_instructor(db, receiver.id, sender.id)
    elif {sender_role, receiver_role} == {"teacher", "faculty"}:
        # This schema has no institution/department membership. Fail closed unless
        # a real course relationship proves the association.
        allowed = await _student_is_enrolled_with_instructor(db, sender.id, receiver.id)
        if not allowed:
            allowed = await _student_is_enrolled_with_instructor(db, receiver.id, sender.id)

    if not allowed:
        logger.warning(
            "messaging_academic_relationship_denied sender_id=%s receiver_id=%s",
            sender.id,
            receiver.id,
        )
        raise forbidden(
            "ACADEMIC_RELATIONSHIP_REQUIRED",
            "An active academic relationship is required for messaging.",
        )
