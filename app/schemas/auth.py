from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# 🔹 Login Request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


# 🔹 Register Request
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)


# 🔹 Token Response
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# 🔹 Token Payload (internal use)
class TokenPayload(BaseModel):
    sub: str          # user_id
    exp: int          # expiry timestamp


# 🔹 Refresh Token Request
class RefreshTokenRequest(BaseModel):
    refresh_token: str


# 🔹 Basic Auth Response (optional)
class AuthResponse(BaseModel):
    user_id: str
    email: EmailStr