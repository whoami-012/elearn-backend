from __future__ import annotations

from enum import Enum

from fastapi import HTTPException, status

from app.models.course import Course
from app.models.user import User


class UserRole(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"
    TEACHER = "teacher"


def normalized_role(role: str | Enum) -> str:
    value = role.value if isinstance(role, Enum) else str(role)
    return value.lower()


def user_role(user: User) -> UserRole | None:
    value = normalized_role(user.role)
    for role in UserRole:
        if role.value == value:
            return role
    return None


def require_active_user(user: User) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    if user.is_deleted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account has been deleted")
    return user


def require_admin(user: User) -> User:
    require_active_user(user)
    if user_role(user) != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_faculty_or_admin(user: User) -> User:
    require_active_user(user)
    if user_role(user) not in {UserRole.FACULTY, UserRole.ADMIN, UserRole.TEACHER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty or admin access required")
    return user


def require_student(user: User) -> User:
    require_active_user(user)
    if user_role(user) != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required")
    return user


def require_course_faculty_or_admin(course: Course, user: User) -> Course:
    require_faculty_or_admin(user)
    if user_role(user) == UserRole.ADMIN:
        return course
    if course.faculty_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not manage this course")
    return course


def require_owner_or_admin(owner_id, user: User, detail: str = "You do not have permission to access this resource") -> User:
    require_active_user(user)
    if user_role(user) == UserRole.ADMIN:
        return user
    if owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return user
