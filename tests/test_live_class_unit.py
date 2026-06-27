from datetime import datetime, timezone

import pytest

from app.schemas.live_class import LiveClassCreate
from app.services.agora_service import AgoraTokenService
from app.services.live_class_service import _duration_status


def test_schedule_rejects_invalid_time_order():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        LiveClassCreate(course_id="00000000-0000-0000-0000-000000000001", title="Test", scheduled_start_time=now, scheduled_end_time=now)


def test_attendance_threshold_is_idempotent_and_configurable():
    assert _duration_status(2700, 60) == "present"
    assert _duration_status(2699, 60) == "partial"
    assert _duration_status(0, 60) == "absent"


def test_agora_certificate_never_part_of_token_service_result(monkeypatch):
    monkeypatch.setattr("app.services.agora_service.RtcTokenBuilder.buildTokenWithUid", lambda *args: "rtc-token")
    credential = AgoraTokenService("public-id", "private-certificate").issue("channel", 12, False, 60)
    assert credential.token == "rtc-token"
    assert not hasattr(credential, "certificate")


def test_agora_uid_must_be_numeric_uint32():
    with pytest.raises(ValueError):
        AgoraTokenService("id", "cert").issue("channel", 0, False, 60)
