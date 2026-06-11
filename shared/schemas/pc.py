from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PCBase(BaseModel):
    name: str
    pc_number: int
    branch_id: int
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None


class PCCreate(PCBase):
    pass


class PCUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class PCResponse(PCBase):
    id: int
    status: str
    is_active: bool
    last_heartbeat_at: Optional[datetime] = None
    current_session_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PCStatus(BaseModel):
    pc_id: int
    status: str
    time_left: float  # in seconds
    is_active: bool
