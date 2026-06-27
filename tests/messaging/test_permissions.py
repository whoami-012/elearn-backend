from app.messaging.permissions import can_users_message


def test_allowed_role_pairs():
    assert can_users_message("student", "teacher")
    assert can_users_message("teacher", "student")
    assert can_users_message("student", "faculty")
    assert can_users_message("faculty", "student")
    assert can_users_message("teacher", "faculty")
    assert can_users_message("faculty", "teacher")


def test_disallowed_role_pairs():
    assert not can_users_message("student", "student")
    assert not can_users_message("faculty", "faculty")
    assert not can_users_message("admin", "student")
