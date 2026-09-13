from pydantic import BaseModel, EmailStr, Field
from typing import Literal


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    # Only allow self-registering as "user" — admins are promoted manually
    # in the DB, never created via a public endpoint. This is a deliberate
    # security decision, not an oversight.


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["admin", "user"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
