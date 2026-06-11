from fastapi import APIRouter, Depends
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

router = APIRouter()


class DashboardOverview(BaseModel):
    total_pcs: int
    online_pcs: int
    active_sessions: int
    total_revenue_today: float
    total_sessions_today: int
    codes_sold_today: int


class RevenueReportResponse(ORMModel):
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


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(branch_id: int = None, db: Prisma = Depends(get_db)):
    # Total PCs
    where_pc = {}
    if branch_id:
        where_pc["branchId"] = branch_id
    
    total_pcs = await db.pc.count(where=where_pc)
    online_pcs = await db.pc.count(
        where={**where_pc, "status": {"in": ["online", "in_use"]}}
    )
    
    # Active sessions
    where_session = {"isActive": True}
    if branch_id:
        where_session["branchId"] = branch_id
    active_sessions = await db.session.count(where=where_session)
    
    # Today's metrics
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    # Revenue today
    where_payment = {"createdAt": {"gte": today_start}}
    if branch_id:
        where_payment["branchId"] = branch_id
    
    # Sessions today
    where_session_today = {"createdAt": {"gte": today_start}}
    if branch_id:
        where_session_today["branchId"] = branch_id
    total_sessions_today = await db.session.count(where=where_session_today)
    
    # Codes sold today
    where_code = {"createdAt": {"gte": today_start}}
    if branch_id:
        where_code["branchId"] = branch_id
    codes_sold_today = await db.code.count(where=where_code)
    
    return DashboardOverview(
        total_pcs=total_pcs,
        online_pcs=online_pcs,
        active_sessions=active_sessions,
        total_revenue_today=0,  # Would need to aggregate payments
        total_sessions_today=total_sessions_today,
        codes_sold_today=codes_sold_today,
    )


@router.get("/revenue", response_model=List[RevenueReportResponse])
async def get_revenue_reports(
    branch_id: int = None,
    start_date: date = None,
    end_date: date = None,
    db: Prisma = Depends(get_db),
):
    where = {}
    if branch_id:
        where["branchId"] = branch_id
    if start_date:
        where["reportDate"] = {"gte": datetime.combine(start_date, datetime.min.time())}
    if end_date:
        if "reportDate" in where:
            where["reportDate"]["lte"] = datetime.combine(end_date, datetime.max.time())
        else:
            where["reportDate"] = {"lte": datetime.combine(end_date, datetime.max.time())}
    
    reports = await db.revenuereport.find_many(
        where=where,
        order={"reportDate": "desc"},
    )
    return reports


@router.post("/revenue/generate")
async def generate_daily_report(
    branch_id: int, report_date: date = None, db: Prisma = Depends(get_db)
):
    if report_date is None:
        report_date = date.today()
    
    # Check if report exists
    existing = await db.revenuereport.find_first(
        where={
            "branchId": branch_id,
            "reportDate": datetime.combine(report_date, datetime.min.time()),
        }
    )
    if existing:
        return {"detail": "Report already exists", "report_id": existing.id}
    
    # Calculate metrics
    day_start = datetime.combine(report_date, datetime.min.time())
    day_end = datetime.combine(report_date, datetime.max.time())
    
    # Total sessions
    total_sessions = await db.session.count(
        where={
            "branchId": branch_id,
            "createdAt": {"gte": day_start, "lte": day_end},
        }
    )
    
    # Total codes used
    total_codes_used = await db.code.count(
        where={
            "branchId": branch_id,
            "usedAt": {"gte": day_start, "lte": day_end},
        }
    )
    
    # Create report
    report = await db.revenuereport.create(
        data={
            "branchId": branch_id,
            "reportDate": datetime.combine(report_date, datetime.min.time()),
            "reportType": "daily",
            "totalRevenue": 0,  # Would need to aggregate payments
            "totalSessions": total_sessions,
            "totalCodesUsed": total_codes_used,
            "averageSessionDuration": 0,
        }
    )
    
    return {"detail": "Report generated", "report_id": report.id}
