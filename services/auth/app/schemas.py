from __future__ import annotations

import uuid
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True


class MeOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class AvatarUploadOut(BaseModel):
    url: str
    status: Optional[str] = "ok"
    message: Optional[str] = "Avatar uploaded"


class AccountActionIn(BaseModel):
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str
