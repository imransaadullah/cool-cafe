"""Security dashboard APIs: audit logs and active alerts."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from pydantic import BaseModel
from shared.database import get_db
from shared.orm_model import ORMModel

router = APIRouter()


class AuditLogResponse(ORMModel):
    id: int
    pc_id: Optional[int] = None
    branch_id: int
    event_type: str
    details: Optional[Any] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    event_type: str
    pc_id: Optional[int] = None
    branch_id: int
    details: Optional[str] = None
    created_at: datetime


class DismissAlertRequest(BaseModel):
    alert_id: int


def _format_details(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    branch_id: Optional[int] = None,
    event_type: Optional[str] = None,
    pc_id: Optional[int] = None,
    limit: int = 100,
    db: Prisma = Depends(get_db),
):
    where: dict = {}
    if branch_id is not None:
        where["branchId"] = branch_id
    if event_type:
        where["eventType"] = event_type
    if pc_id is not None:
        where["pcId"] = pc_id

    logs = await db.securityauditlog.find_many(
        where=where,
        order={"createdAt": "desc"},
        take=min(limit, 500),
    )
    return [
        AuditLogResponse(
            id=log.id,
            pc_id=log.pcId,
            branch_id=log.branchId,
            event_type=log.eventType,
            details=_format_details(log.details),
            ip_address=log.ipAddress,
            created_at=log.createdAt,
        )
        for log in logs
    ]


@router.get("/alerts", response_model=List[AlertResponse])
async def list_active_alerts(
    branch_id: Optional[int] = None,
    db: Prisma = Depends(get_db),
):
    """Active alarms: PCs currently alarming plus recent bypass attempts."""
    pc_where: dict = {"isAlarming": True}
    if branch_id is not None:
        pc_where["branchId"] = branch_id

    alarming_pcs = await db.pc.find_many(where=pc_where)
    alerts: List[AlertResponse] = []

    for pc in alarming_pcs:
        log = await db.securityauditlog.find_first(
            where={
                "pcId": pc.id,
                "eventType": "alarm_triggered",
            },
            order={"createdAt": "desc"},
        )
        details = _format_details(log.details) if log else {"reason": "active alarm"}
        if isinstance(details, dict):
            details_str = details.get("reason") or json.dumps(details)
        else:
            details_str = str(details) if details else "Alarm active"

        alerts.append(
            AlertResponse(
                id=log.id if log else pc.id,
                event_type="alarm_triggered",
                pc_id=pc.id,
                branch_id=pc.branchId,
                details=details_str,
                created_at=log.createdAt if log else pc.updatedAt,
            )
        )

    bypass_where: dict = {"eventType": "bypass_attempt"}
    if branch_id is not None:
        bypass_where["branchId"] = branch_id
    recent_bypass = await db.securityauditlog.find_many(
        where=bypass_where,
        order={"createdAt": "desc"},
        take=10,
    )
    for log in recent_bypass:
        details = _format_details(log.details)
        if isinstance(details, dict):
            details_str = details.get("method") or json.dumps(details)
        else:
            details_str = str(details) if details else "Bypass attempt"
        alerts.append(
            AlertResponse(
                id=log.id,
                event_type=log.eventType,
                pc_id=log.pcId,
                branch_id=log.branchId,
                details=details_str,
                created_at=log.createdAt,
            )
        )

    return alerts


@router.post("/dismiss-alert")
async def dismiss_alert(
    body: DismissAlertRequest,
    db: Prisma = Depends(get_db),
):
    """Dismiss an alarm alert by resetting the PC alarm state."""
    log = await db.securityauditlog.find_unique(where={"id": body.alert_id})
    if not log:
        raise HTTPException(status_code=404, detail="Alert not found")

    if log.pcId and log.eventType == "alarm_triggered":
        await db.pc.update(
            where={"id": log.pcId},
            data={"isAlarming": False},
        )
        await db.securityauditlog.create(
            data={
                "pcId": log.pcId,
                "branchId": log.branchId,
                "eventType": "alarm_dismissed",
                "details": {"source_alert_id": body.alert_id},
            }
        )

    return {"detail": "Alert dismissed"}
