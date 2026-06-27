from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import time

from agora_token_builder import RtcTokenBuilder
from dotenv import load_dotenv

from app.core.config import settings


@dataclass(frozen=True)
class AgoraCredential:
    token: str
    expires_at: datetime


class AgoraTokenService:
    def __init__(self, app_id: str | None = None, certificate: str | None = None):
        # Resolve the backend env file independently of Uvicorn's working
        # directory and Windows reload-worker environment inheritance.
        load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
        self.app_id = app_id if app_id is not None else os.getenv("AGORA_APP_ID", settings.AGORA_APP_ID)
        self.certificate = certificate if certificate is not None else os.getenv(
            "AGORA_APP_CERTIFICATE", settings.AGORA_APP_CERTIFICATE
        )

    def issue(self, channel: str, uid: int, broadcaster: bool, duration_minutes: int) -> AgoraCredential:
        if not self.app_id or not self.certificate:
            raise RuntimeError("Agora credentials are not configured")
        if not 0 < uid <= 0xFFFFFFFF:
            raise ValueError("Agora UID must be an unsigned 32-bit integer")
        lifetime = max(60, min(120, duration_minutes + settings.LIVE_CLASS_TOKEN_BUFFER_MINUTES))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=lifetime)
        role = 1 if broadcaster else 2  # Publisher / Subscriber in agora-token-builder
        token = RtcTokenBuilder.buildTokenWithUid(
            self.app_id, self.certificate, channel, uid, role, int(expires_at.timestamp())
        )
        return AgoraCredential(token=token, expires_at=expires_at)
