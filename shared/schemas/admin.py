from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AdminBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "branch_admin"
    branch_id: Optional[int] = None


class AdminCreate(AdminBase):
    password: str


class AdminUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None
    is_active: Optional[bool] = None


class AdminResponse(AdminBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[int] = None
