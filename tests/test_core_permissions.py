from fastapi import HTTPException

from app.core.permissions import (
    UserRole,
    normalized_role,
    require_admin,
    require_course_faculty_or_admin,
)
from app.models.course import Course
from app.models.user import User


def test_normalized_role_is_case_insensitive():
    assert normalized_role("ADMIN") == UserRole.ADMIN.value


def test_require_admin_rejects_non_admin():
    user = User(name="Student", email="student@test.com", role="student", is_active=True, is_deleted=False)
    try:
        require_admin(user)
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Admin access required"
    else:
        raise AssertionError("Expected HTTPException")


def test_require_course_faculty_or_admin_allows_course_owner():
    user = User(name="Faculty", email="faculty@test.com", role="faculty", is_active=True, is_deleted=False)
    user.id = "owner-id"
    course = Course(title="Course", description="Description text", price=0, is_free=True)
    course.faculty_id = "owner-id"
    assert require_course_faculty_or_admin(course, user) is course
