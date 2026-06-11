from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SessionBase(BaseModel):
    pc_id: int
    branch_id: int
    duration_minutes: float


class SessionCreate(SessionBase):
    code: Optional[str] = None
    code_id: Optional[int] = None


class SessionUpdate(BaseModel):
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    remaining_minutes: Optional[float] = None


class SessionResponse(SessionBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    total_paused_minutes: float
    remaining_minutes: Optional[float] = None
    status: str
    is_active: bool
    amount_charged: float
    created_at: datetime

    class Config:
        from_attributes = True


class HeartbeatResponse(BaseModel):
    status: str  # active, paused, expired, locked
    time_left: float  # in seconds
    is_active: bool
    session_id: Optional[int] = None


class CodeRedeemRequest(BaseModel):
    code: str
    pc_id: int


class CodeRedeemResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[int] = None
    duration_minutes: Optional[float] = None
    end_time: Optional[datetime] = None
