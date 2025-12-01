from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Base Schema (Shared properties)
class UserBase(BaseModel):
    username: str
    email: EmailStr

# Schema for creating a user (Password required)
class UserCreate(UserBase):
    password: str

# Schema for logging in
class UserLogin(BaseModel):
    username: str
    password: str

# Schema for returning user data (NEVER return the password)
class UserResponse(UserBase):
    id: int
    rating: int
    created_at: datetime
    is_active: bool

    class ConfigDict:
        from_attributes = True