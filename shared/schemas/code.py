from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class CodeBatchBase(BaseModel):
    branch_id: int
    count: int
    duration_minutes: float
    value_per_code: float = 0
    batch_name: Optional[str] = None


class CodeBatchCreate(CodeBatchBase):
    pass


class CodeBatchResponse(CodeBatchBase):
    id: int
    is_active: bool
    printed: bool
    printed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CodeBase(BaseModel):
    code: str
    duration_minutes: float
    branch_id: int
    value: float = 0


class CodeCreate(CodeBase):
    batch_id: Optional[int] = None


class CodeResponse(CodeBase):
    id: int
    batch_id: Optional[int] = None
    is_used: bool
    used_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RevenueReportResponse(BaseModel):
    id: int
    branch_id: int
    report_date: date
    report_type: str
    total_revenue: float
    total_sessions: int
    total_codes_used: int
    total_paused_sessions: int
    average_session_duration: float
    generated_at: datetime

    class Config:
        from_attributes = True


class DashboardOverview(BaseModel):
    total_pcs: int
    online_pcs: int
    active_sessions: int
    total_revenue_today: float
    total_sessions_today: int
    codes_sold_today: int
