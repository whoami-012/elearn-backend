from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID


# 🔹 Login Request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class GoogleLoginUser(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    profile_image: str | None = None

    class Config:
        from_attributes = True


class GoogleLoginResponse(BaseModel):
    success: bool = True
    message: str = "Google login successful"
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: GoogleLoginUser


class AppleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)
    first_name: str | None = None
    last_name: str | None = None


class AppleLoginResponse(GoogleLoginResponse):
    message: str = "Apple login successful"


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
