"""Apply synced records from local branches on the global server."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from prisma import Prisma

logger = logging.getLogger(__name__)

TABLE_HANDLERS = {
    "payments",
    "sessions",
    "revenue_reports",
    "branches",
}


async def apply_sync_item(
    db: Prisma,
    action_type: str,
    table_name: str,
    record_id: str,
    payload: Dict[str, Any],
) -> bool:
    """Apply a single sync payload to the global database."""
    if table_name not in TABLE_HANDLERS:
        logger.warning("Unknown sync table: %s", table_name)
        return False

    if table_name == "payments":
        return await _apply_payment(db, action_type, record_id, payload)
    if table_name == "sessions":
        return await _apply_session(db, action_type, record_id, payload)
    if table_name == "revenue_reports":
        return await _apply_revenue_report(db, action_type, record_id, payload)
    if table_name == "branches":
        return await _apply_branch(db, action_type, record_id, payload)
    return False


async def _apply_payment(db: Prisma, action_type: str, record_id: str, payload: Dict[str, Any]) -> bool:
    local_id = payload.get("local_id") or record_id
    existing = await db.payment.find_unique(where={"localId": local_id})
    if action_type == "delete" and existing:
        await db.payment.delete(where={"id": existing.id})
        return True
    if existing:
        await db.payment.update(
            where={"id": existing.id},
            data={
                "amount": payload.get("amount", existing.amount),
                "status": payload.get("status", existing.status),
                "method": payload.get("method", existing.method),
                "synced": True,
            },
        )
        return True
    await db.payment.create(
        data={
            "branchId": payload["branch_id"],
            "sessionId": payload.get("session_id"),
            "amount": payload["amount"],
            "method": payload.get("method", "cash"),
            "status": payload.get("status", "completed"),
            "localId": local_id,
            "synced": True,
        }
    )
    return True


async def _apply_session(db: Prisma, action_type: str, record_id: str, payload: Dict[str, Any]) -> bool:
    local_id = payload.get("local_id") or record_id
    existing = await db.session.find_first(where={"localId": local_id})
    if action_type == "delete" and existing:
        await db.session.delete(where={"id": existing.id})
        return True
    if existing:
        await db.session.update(
            where={"id": existing.id},
            data={
                "status": payload.get("status", existing.status),
                "amountCharged": payload.get("amount_charged", existing.amountCharged),
                "synced": True,
            },
        )
        return True
    return False


async def _apply_revenue_report(
    db: Prisma, action_type: str, record_id: str, payload: Dict[str, Any]
) -> bool:
    local_id = payload.get("local_id") or record_id
    existing = await db.revenuereport.find_unique(where={"localId": local_id})
    if existing:
        await db.revenuereport.update(
            where={"id": existing.id},
            data={
                "totalRevenue": payload.get("total_revenue", existing.totalRevenue),
                "totalSessions": payload.get("total_sessions", existing.totalSessions),
                "synced": True,
            },
        )
        return True
    report_date = payload.get("report_date")
    if isinstance(report_date, str):
        report_date = datetime.fromisoformat(report_date.replace("Z", "+00:00"))
    await db.revenuereport.create(
        data={
            "branchId": payload["branch_id"],
            "reportDate": report_date or datetime.utcnow(),
            "reportType": payload.get("report_type", "daily"),
            "totalRevenue": payload.get("total_revenue", 0),
            "totalSessions": payload.get("total_sessions", 0),
            "totalCodesUsed": payload.get("total_codes_used", 0),
            "averageSessionDuration": payload.get("average_session_duration", 0),
            "localId": local_id,
            "synced": True,
        }
    )
    return True


async def _apply_branch(db: Prisma, action_type: str, record_id: str, payload: Dict[str, Any]) -> bool:
    global_id = payload.get("global_id") or int(record_id)
    existing = await db.branch.find_unique(where={"globalId": global_id})
    if existing:
        await db.branch.update(
            where={"id": existing.id},
            data={
                "name": payload.get("name", existing.name),
                "lastSyncAt": datetime.utcnow(),
            },
        )
        return True
    await db.branch.create(
        data={
            "name": payload.get("name", f"Branch {global_id}"),
            "globalId": global_id,
            "lastSyncAt": datetime.utcnow(),
        }
    )
    return True


async def process_pending_queue(db: Prisma, limit: int = 100) -> int:
    """Process unsynced items in the global offline queue."""
    pending = await db.offlinequeue.find_many(
        where={"synced": False},
        order={"createdAt": "asc"},
        take=limit,
    )
    processed = 0
    for item in pending:
        try:
            import json
            payload = json.loads(item.payload)
            ok = await apply_sync_item(
                db,
                item.actionType,
                item.tableName,
                item.recordId,
                payload,
            )
            if ok:
                await db.offlinequeue.update(
                    where={"id": item.id},
                    data={"synced": True, "syncedAt": datetime.utcnow()},
                )
                processed += 1
        except Exception as exc:
            logger.error("Failed to process queue item %s: %s", item.id, exc)
            await db.offlinequeue.update(
                where={"id": item.id},
                data={
                    "retryCount": item.retryCount + 1,
                    "errorMessage": str(exc)[:500],
                },
            )
    return processed
