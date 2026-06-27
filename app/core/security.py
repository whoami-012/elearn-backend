import bcrypt
from datetime import datetime, timedelta
from jose import jwt
from .config import settings

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(sub: str, role: str, expires_minutes: int = None) -> str:
    """
    Create a short-lived JWT access token.
    Includes a 'type': 'access' claim so it cannot be used as a refresh token.
    """
    exp = datetime.utcnow() + timedelta(
        minutes=(expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": sub, "role": role, "exp": exp, "type": "access"}  # Fix #6: type claim added
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(sub: str, role: str) -> str:  # Fix #5: renamed + fixed NameError
    """
    Create a long-lived JWT refresh token.
    Uses REFRESH_TOKEN_EXPIRE_DAYS from settings and a dedicated 'type': 'refresh'
    claim so it is distinguishable from and cannot be used in place of an access token.
    """
    exp = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS  # Fix #5: uses its own TTL, not access TTL
    )
    payload = {"sub": sub, "role": role, "exp": exp, "type": "refresh"}  # Fix #6: type claim
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
