"""Revenue aggregation from payments and session charges."""

from __future__ import annotations

from datetime import datetime, date
from prisma import Prisma


async def sum_revenue(
    db: Prisma,
    branch_id: int | None,
    start: datetime,
    end: datetime,
) -> float:
    """Total completed payments plus session charges in a date range."""
    payment_where: dict = {
        "createdAt": {"gte": start, "lte": end},
        "status": "completed",
    }
    session_where: dict = {
        "createdAt": {"gte": start, "lte": end},
    }
    if branch_id is not None:
        payment_where["branchId"] = branch_id
        session_where["branchId"] = branch_id

    payments = await db.payment.find_many(where=payment_where)
    payment_total = sum(p.amount for p in payments)

    sessions = await db.session.find_many(where=session_where)
    session_total = sum(s.amountCharged or 0 for s in sessions)

    # Payments linked to sessions are already in payment_total; use max of both
    # approaches to avoid double-count when amountCharged mirrors payment.
    linked_session_ids = {p.sessionId for p in payments if p.sessionId}
    unlinked_session_total = sum(
        s.amountCharged or 0
        for s in sessions
        if s.id not in linked_session_ids
    )
    return payment_total + unlinked_session_total


async def compute_daily_metrics(
    db: Prisma,
    branch_id: int,
    report_date: date,
) -> dict:
    """Compute revenue report metrics for a single day."""
    day_start = datetime.combine(report_date, datetime.min.time())
    day_end = datetime.combine(report_date, datetime.max.time())

    sessions = await db.session.find_many(
        where={
            "branchId": branch_id,
            "createdAt": {"gte": day_start, "lte": day_end},
        }
    )
    total_sessions = len(sessions)
    paused_count = sum(1 for s in sessions if s.status == "paused")

    durations = [
        s.durationMinutes or 0
        for s in sessions
        if s.durationMinutes
    ]
    avg_duration = sum(durations) / len(durations) if durations else 0

    total_codes_used = await db.code.count(
        where={
            "branchId": branch_id,
            "usedAt": {"gte": day_start, "lte": day_end},
        }
    )

    total_revenue = await sum_revenue(db, branch_id, day_start, day_end)

    # Peak hour from session start times
    hour_counts: dict[int, int] = {}
    for s in sessions:
        if s.startTime:
            hour = s.startTime.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
    peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None

    return {
        "total_revenue": total_revenue,
        "total_sessions": total_sessions,
        "total_codes_used": total_codes_used,
        "total_paused_sessions": paused_count,
        "average_session_duration": avg_duration,
        "peak_hour_start": peak_hour,
        "peak_hour_end": (peak_hour + 1) if peak_hour is not None else None,
    }
