import pytest
from fastapi import HTTPException

from app.messaging.permissions import can_users_message, validate_role_pair
from app.models.user import User


def test_allowed_role_pairs():
    assert can_users_message("student", "teacher")
    assert can_users_message("teacher", "student")
    assert can_users_message("student", "faculty")
    assert can_users_message("faculty", "student")
    assert can_users_message("teacher", "faculty")
    assert can_users_message("faculty", "teacher")
    assert can_users_message("admin", "student")
    assert can_users_message("student", "admin")
    assert can_users_message("admin", "faculty")
    assert can_users_message("faculty", "admin")
    assert can_users_message("admin", "admin")


def test_disallowed_role_pairs():
    assert not can_users_message("student", "student")
    assert not can_users_message("faculty", "faculty")
    assert not can_users_message("student", "unknown")


def test_inactive_users_cannot_message():
    sender = User(name="Admin", email="admin@test.com", role="admin", is_active=True, is_deleted=False)
    receiver = User(name="Student", email="student@test.com", role="student", is_active=False, is_deleted=False)
    with pytest.raises(HTTPException):
        validate_role_pair(sender, receiver)
