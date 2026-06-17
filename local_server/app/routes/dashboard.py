from fastapi import APIRouter, Depends
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from ..services.revenue import sum_revenue, compute_daily_metrics
from ..services.sync_worker import queue_sync_event
import uuid

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

    today_end = datetime.combine(date.today(), datetime.max.time())
    total_revenue_today = await sum_revenue(db, branch_id, today_start, today_end)
    
    return DashboardOverview(
        total_pcs=total_pcs,
        online_pcs=online_pcs,
        active_sessions=active_sessions,
        total_revenue_today=total_revenue_today,
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
    
    metrics = await compute_daily_metrics(db, branch_id, report_date)
    
    report = await db.revenuereport.create(
        data={
            "branchId": branch_id,
            "reportDate": datetime.combine(report_date, datetime.min.time()),
            "reportType": "daily",
            "totalRevenue": metrics["total_revenue"],
            "totalSessions": metrics["total_sessions"],
            "totalCodesUsed": metrics["total_codes_used"],
            "totalPausedSessions": metrics["total_paused_sessions"],
            "averageSessionDuration": metrics["average_session_duration"],
            "peakHourStart": metrics["peak_hour_start"],
            "peakHourEnd": metrics["peak_hour_end"],
            "localId": str(uuid.uuid4()),
        }
    )

    await queue_sync_event(
        db,
        "upsert",
        "revenue_reports",
        str(report.id),
        {
            "local_id": report.localId,
            "branch_id": branch_id,
            "report_date": report_date.isoformat(),
            "report_type": "daily",
            "total_revenue": metrics["total_revenue"],
            "total_sessions": metrics["total_sessions"],
            "total_codes_used": metrics["total_codes_used"],
            "average_session_duration": metrics["average_session_duration"],
        },
    )
    
    return {"detail": "Report generated", "report_id": report.id}
