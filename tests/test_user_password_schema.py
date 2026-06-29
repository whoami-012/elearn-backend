import pytest
from pydantic import ValidationError

from app.schemas.user import UserPasswordRequest


def test_user_password_request_accepts_valid_new_password():
    request = UserPasswordRequest(
        current_password="CurrentPassword1",
        new_password="NewPassword1",
    )

    assert request.new_password == "NewPassword1"


def test_user_password_request_rejects_short_new_password():
    with pytest.raises(ValidationError, match="Password must be at least 8 characters"):
        UserPasswordRequest(current_password="CurrentPassword1", new_password="Short1")


def test_user_password_request_requires_uppercase_new_password():
    with pytest.raises(ValidationError, match="Password must contain an uppercase letter"):
        UserPasswordRequest(current_password="CurrentPassword1", new_password="lowercase1")
