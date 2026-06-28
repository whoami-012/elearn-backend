from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import auth_service


def _configure(monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "settings",
        SimpleNamespace(GOOGLE_CLIENT_ID="client.apps.googleusercontent.com"),
    )


def test_google_token_verification_uses_configured_audience(monkeypatch):
    _configure(monkeypatch)
    captured = {}

    def fake_verify(token, request, audience):
        captured.update(token=token, audience=audience)
        return {
            "sub": "google-user-1",
            "email": "Student@Gmail.com",
            "email_verified": True,
        }

    monkeypatch.setattr(auth_service.google_id_token, "verify_oauth2_token", fake_verify)

    claims = auth_service.verify_google_id_token("valid-token")

    assert claims["sub"] == "google-user-1"
    assert captured == {
        "token": "valid-token",
        "audience": "client.apps.googleusercontent.com",
    }


@pytest.mark.parametrize("error", [ValueError("invalid"), ValueError("expired")])
def test_google_token_verification_rejects_invalid_or_expired_token(monkeypatch, error):
    _configure(monkeypatch)

    def fake_verify(*args, **kwargs):
        raise error

    monkeypatch.setattr(auth_service.google_id_token, "verify_oauth2_token", fake_verify)

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_google_id_token("bad-token")

    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    ("claims", "status_code"),
    [
        ({"sub": "1", "email_verified": True}, 400),
        ({"sub": "1", "email": "student@gmail.com", "email_verified": False}, 403),
        ({"email": "student@gmail.com", "email_verified": True}, 401),
    ],
)
def test_google_token_verification_validates_required_claims(monkeypatch, claims, status_code):
    _configure(monkeypatch)
    monkeypatch.setattr(
        auth_service.google_id_token,
        "verify_oauth2_token",
        lambda *args, **kwargs: claims,
    )

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_google_id_token("token")

    assert exc.value.status_code == status_code


def test_google_login_requires_backend_configuration(monkeypatch):
    monkeypatch.setattr(auth_service, "settings", SimpleNamespace(GOOGLE_CLIENT_ID=""))

    with pytest.raises(HTTPException) as exc:
        auth_service.verify_google_id_token("token")

    assert exc.value.status_code == 503
