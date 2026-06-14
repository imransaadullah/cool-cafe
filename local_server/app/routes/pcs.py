from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from shared.pc_config import dump_pc_config, parse_pc_config, pop_pending_commands, queue_command
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import secrets
import string
import random

from ..services.client_config_builder import build_client_config

router = APIRouter()


class PCCreate(BaseModel):
    name: str
    pc_number: int
    branch_id: int
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None


class PCUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class PCResponse(ORMModel):
    id: int
    name: str
    pc_number: int
    branch_id: int
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
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
    time_left: float
    is_active: bool


class HeartbeatRequest(BaseModel):
    status: str = "online"
    session_active: bool = False
    app_version: Optional[str] = None
    platform: Optional[str] = None


class HeartbeatResponse(BaseModel):
    success: bool
    server_time: datetime
    is_banned: bool
    alarm_active: bool
    commands: List[Dict[str, Any]] = []
    app_policy: Optional[dict] = None
    client_mode: Optional[str] = None
    config_updates: Optional[dict] = None


class AppPolicyUpdate(BaseModel):
    mode: Optional[str] = None
    allowed_apps: Optional[List[str]] = None
    blocked_apps: Optional[List[str]] = None


class PCAppPolicyUpdate(BaseModel):
    app_policy: AppPolicyUpdate


class PCCommandRequest(BaseModel):
    reason: Optional[str] = None


class BanRequest(BaseModel):
    reason: Optional[str] = None


class RegisterStaticCodeRequest(BaseModel):
    static_master_code: str
    recovery_key_combo: str


class PCConfigUpdate(BaseModel):
    auto_start_enabled: Optional[bool] = None
    run_as_service: Optional[bool] = None
    alarm_enabled: Optional[bool] = None
    alarm_color: Optional[str] = None
    client_mode: Optional[str] = None
    app_policy: Optional[AppPolicyUpdate] = None


class PCFullStatus(BaseModel):
    id: int
    name: str
    pc_number: int
    status: str
    is_active: bool
    client_running: bool
    is_banned: bool
    is_alarming: bool
    last_heartbeat_at: Optional[datetime] = None
    wrong_code_attempts: int
    static_code_used_at: Optional[datetime] = None
    last_bypass_at: Optional[datetime] = None
    has_active_session: bool
    time_left: float
    session_code: Optional[str] = None
    session_status: Optional[str] = None


def generate_recovery_combo() -> str:
    """Generate random recovery key combination."""
    keys_pool = (
        [f"F{i}" for i in range(1, 13)] +
        list(string.ascii_uppercase) +
        list(string.digits)
    )
    combo = random.sample(keys_pool, 3)
    return "+".join(combo)


@router.get("/", response_model=List[PCResponse])
async def get_pcs(branch_id: int = None, db: Prisma = Depends(get_db)):
    if branch_id:
        pcs = await db.pc.find_many(where={"branchId": branch_id})
    else:
        pcs = await db.pc.find_many()
    return pcs


@router.get("/status", response_model=List[PCFullStatus])
async def get_all_pc_status(branch_id: int = None, db: Prisma = Depends(get_db)):
    """Get full status of all PCs (for dashboard)."""
    if branch_id:
        pcs = await db.pc.find_many(where={"branchId": branch_id})
    else:
        pcs = await db.pc.find_many()
    
    result = []
    for pc in pcs:
        has_session = False
        time_left = 0
        session_code = None
        session_status = None

        if pc.currentSessionId:
            session = await db.session.find_unique(where={"id": pc.currentSessionId})
            if session and session.isActive:
                has_session = True
                session_status = session.status
                if session.codeId:
                    code = await db.code.find_unique(where={"id": session.codeId})
                    if code:
                        session_code = code.code
                if session.status == "active":
                    elapsed = (
                        datetime.now(timezone.utc) - session.startTime
                    ).total_seconds() / 60
                    paused = session.totalPausedMinutes or 0
                    remaining = session.durationMinutes - elapsed + paused
                    time_left = max(0, remaining * 60)
                elif session.status == "paused":
                    time_left = (session.remainingMinutes or 0) * 60

        result.append(PCFullStatus(
            id=pc.id,
            name=pc.name,
            pc_number=pc.pcNumber,
            status=pc.status,
            is_active=pc.isActive,
            client_running=pc.clientRunning,
            is_banned=pc.isBanned,
            is_alarming=pc.isAlarming,
            last_heartbeat_at=pc.lastHeartbeatAt,
            wrong_code_attempts=pc.wrongCodeAttempts,
            static_code_used_at=pc.staticCodeUsedAt,
            last_bypass_at=pc.lastBypassAt,
            has_active_session=has_session,
            time_left=time_left,
            session_code=session_code,
            session_status=session_status,
        ))
    
    return result


@router.post("/register", response_model=PCResponse)
async def register_pc(pc_data: PCCreate, db: Prisma = Depends(get_db)):
    """Register or update a PC from client setup (lookup by branch + pc_number)."""
    existing = await db.pc.find_first(
        where={
            "branchId": pc_data.branch_id,
            "pcNumber": pc_data.pc_number,
        }
    )

    if existing:
        update_data = {"name": pc_data.name}
        if pc_data.ip_address is not None:
            update_data["ipAddress"] = pc_data.ip_address
        if pc_data.mac_address is not None:
            update_data["macAddress"] = pc_data.mac_address
        return await db.pc.update(where={"id": existing.id}, data=update_data)

    return await db.pc.create(
        data={
            "name": pc_data.name,
            "pcNumber": pc_data.pc_number,
            "branchId": pc_data.branch_id,
            "ipAddress": pc_data.ip_address,
            "macAddress": pc_data.mac_address,
        }
    )


@router.get("/{pc_id}", response_model=PCResponse)
async def get_pc(pc_id: int, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    return pc


@router.post("/", response_model=PCResponse)
async def create_pc(pc_data: PCCreate, db: Prisma = Depends(get_db)):
    pc = await db.pc.create(
        data={
            "name": pc_data.name,
            "pcNumber": pc_data.pc_number,
            "branchId": pc_data.branch_id,
            "ipAddress": pc_data.ip_address,
            "macAddress": pc_data.mac_address,
        }
    )
    return pc


@router.put("/{pc_id}", response_model=PCResponse)
async def update_pc(pc_id: int, pc_data: PCUpdate, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    update_data = {}
    if pc_data.name is not None:
        update_data["name"] = pc_data.name
    if pc_data.ip_address is not None:
        update_data["ipAddress"] = pc_data.ip_address
    if pc_data.mac_address is not None:
        update_data["macAddress"] = pc_data.mac_address
    if pc_data.status is not None:
        update_data["status"] = pc_data.status
    if pc_data.is_active is not None:
        update_data["isActive"] = pc_data.is_active
    
    updated_pc = await db.pc.update(
        where={"id": pc_id},
        data=update_data,
    )
    return updated_pc


@router.get("/{pc_id}/status", response_model=PCStatus)
async def get_pc_status(pc_id: int, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    time_left = 0
    is_active = False
    
    if pc.currentSessionId:
        session = await db.session.find_unique(where={"id": pc.currentSessionId})
        if session and session.isActive:
            if session.status == "active":
                elapsed = (datetime.now(timezone.utc) - session.startTime).total_seconds() / 60
                paused = session.totalPausedMinutes or 0
                remaining = session.durationMinutes - elapsed + paused
                if remaining > 0:
                    time_left = remaining * 60
                    is_active = True
            elif session.status == "paused":
                time_left = (session.remainingMinutes or 0) * 60
                is_active = True
    
    return PCStatus(
        pc_id=pc.id,
        status=pc.status,
        time_left=time_left,
        is_active=is_active,
    )


async def _queue_pc_command(
    db: Prisma,
    pc_id: int,
    command_type: str,
    payload: Optional[dict] = None,
) -> None:
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    config = parse_pc_config(pc.config)
    queue_command(
        config,
        {
            "type": command_type,
            "payload": payload or {},
            "id": secrets.token_hex(8),
        },
    )
    await db.pc.update(
        where={"id": pc_id},
        data={"config": dump_pc_config(config)},
    )


@router.post("/{pc_id}/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(pc_id: int, data: HeartbeatRequest, db: Prisma = Depends(get_db)):
    """Client heartbeat endpoint."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    config = parse_pc_config(pc.config)
    commands = pop_pending_commands(config)

    client_config = await build_client_config(db, pc)

    await db.pc.update(
        where={"id": pc_id},
        data={
            "lastHeartbeatAt": datetime.now(timezone.utc),
            "clientRunning": True,
            "status": "online" if data.status == "online" else data.status,
            "config": dump_pc_config(config),
        },
    )

    return HeartbeatResponse(
        success=True,
        server_time=datetime.now(timezone.utc),
        is_banned=pc.isBanned,
        alarm_active=pc.isAlarming,
        commands=commands,
        app_policy=client_config.get("app_policy"),
        client_mode=client_config.get("client_mode"),
        config_updates=client_config,
    )


@router.post("/{pc_id}/ban")
async def ban_pc(pc_id: int, data: BanRequest, db: Prisma = Depends(get_db)):
    """Ban a PC (no logins allowed)."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.update(
        where={"id": pc_id},
        data={"isBanned": True}
    )
    
    # Log to audit
    await db.securityauditlog.create(
        data={
            "pcId": pc_id,
            "branchId": pc.branchId,
            "eventType": "pc_banned",
            "details": {"reason": data.reason} if data.reason else None,
        }
    )
    
    return {"message": "PC banned successfully"}


@router.post("/{pc_id}/unban")
async def unban_pc(pc_id: int, db: Prisma = Depends(get_db)):
    """Unban a PC."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.update(
        where={"id": pc_id},
        data={"isBanned": False}
    )
    
    # Log to audit
    await db.securityauditlog.create(
        data={
            "pcId": pc_id,
            "branchId": pc.branchId,
            "eventType": "pc_unbanned",
        }
    )
    
    return {"message": "PC unbanned successfully"}


@router.post("/{pc_id}/register-static-code")
async def register_static_code(pc_id: int, data: RegisterStaticCodeRequest, db: Prisma = Depends(get_db)):
    """Register static master code and recovery combo (during setup)."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.update(
        where={"id": pc_id},
        data={
            "staticMasterCode": data.static_master_code,
            "recoveryKeyCombo": data.recovery_key_combo,
        }
    )
    
    # Log to audit
    await db.securityauditlog.create(
        data={
            "pcId": pc_id,
            "branchId": pc.branchId,
            "eventType": "static_code_registered",
            "details": {"recovery_combo": data.recovery_key_combo},
        }
    )
    
    return {"message": "Static code and recovery combo registered"}


@router.post("/{pc_id}/report-alarm")
async def report_alarm(pc_id: int, db: Prisma = Depends(get_db)):
    """Client reports alarm triggered."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.update(
        where={"id": pc_id},
        data={
            "isAlarming": True,
            "lastAlarmAt": datetime.now(timezone.utc),
        }
    )
    
    # Log to audit
    await db.securityauditlog.create(
        data={
            "pcId": pc_id,
            "branchId": pc.branchId,
            "eventType": "alarm_triggered",
        }
    )
    
    return {"message": "Alarm reported"}


@router.post("/{pc_id}/reset-alarm")
async def reset_alarm(pc_id: int, db: Prisma = Depends(get_db)):
    """Admin resets alarm state."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.update(
        where={"id": pc_id},
        data={
            "isAlarming": False,
            "wrongCodeAttempts": 0,
        }
    )
    
    # Log to audit
    await db.securityauditlog.create(
        data={
            "pcId": pc_id,
            "branchId": pc.branchId,
            "eventType": "alarm_reset",
        }
    )
    
    return {"message": "Alarm reset"}


@router.post("/{pc_id}/report-bypass")
async def report_bypass(pc_id: int, event_type: str, db: Prisma = Depends(get_db)):
    """Client reports bypass attempt."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.update(
        where={"id": pc_id},
        data={
            "lastBypassAt": datetime.now(timezone.utc),
            "clientRunning": False,
        }
    )
    
    # Log to audit
    await db.securityauditlog.create(
        data={
            "pcId": pc_id,
            "branchId": pc.branchId,
            "eventType": event_type,
        }
    )
    
    return {"message": "Bypass reported"}


@router.get("/{pc_id}/config")
async def get_pc_config(pc_id: int, db: Prisma = Depends(get_db)):
    """Get PC security config."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    client_config = await build_client_config(db, pc)
    pc_config = parse_pc_config(pc.config)

    return {
        "auto_start_enabled": pc.autoStartEnabled,
        "run_as_service": pc.runAsService,
        "alarm_enabled": pc.alarmEnabled,
        "alarm_color": pc.alarmColor,
        "recovery_key_combo": pc.recoveryKeyCombo,
        "is_banned": pc.isBanned,
        "client_mode": client_config.get("client_mode"),
        "app_policy": client_config.get("app_policy"),
        "pc_app_policy": pc_config.get("app_policy"),
    }


@router.get("/{pc_id}/client-config")
async def get_pc_client_config(pc_id: int, db: Prisma = Depends(get_db)):
    """Full merged client config for a PC."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    return await build_client_config(db, pc)


@router.put("/{pc_id}/config")
async def update_pc_config(pc_id: int, data: PCConfigUpdate, db: Prisma = Depends(get_db)):
    """Update PC config (admin only)."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    update_data = {}
    if data.auto_start_enabled is not None:
        update_data["autoStartEnabled"] = data.auto_start_enabled
    if data.run_as_service is not None:
        update_data["runAsService"] = data.run_as_service
    if data.alarm_enabled is not None:
        update_data["alarmEnabled"] = data.alarm_enabled
    if data.alarm_color is not None:
        update_data["alarmColor"] = data.alarm_color

    config = parse_pc_config(pc.config)
    if data.client_mode is not None:
        config["client_mode"] = data.client_mode
    if data.app_policy is not None:
        existing = config.get("app_policy", {})
        if not isinstance(existing, dict):
            existing = {}
        policy_update = data.app_policy.model_dump(exclude_none=True)
        existing.update(policy_update)
        config["app_policy"] = existing
        update_data["config"] = dump_pc_config(config)

    await db.pc.update(
        where={"id": pc_id},
        data=update_data,
    )

    return {"message": "Config updated"}


@router.put("/{pc_id}/app-policy")
async def update_pc_app_policy(
    pc_id: int,
    data: PCAppPolicyUpdate,
    db: Prisma = Depends(get_db),
):
    """Update per-PC app policy overrides."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    config = parse_pc_config(pc.config)
    existing = config.get("app_policy", {})
    if not isinstance(existing, dict):
        existing = {}
    existing.update(data.app_policy.model_dump(exclude_none=True))
    config["app_policy"] = existing

    await db.pc.update(
        where={"id": pc_id},
        data={"config": dump_pc_config(config)},
    )
    return {"message": "PC app policy updated", "app_policy": existing}


@router.post("/{pc_id}/commands/force-lock")
async def force_lock_pc(
    pc_id: int,
    data: PCCommandRequest = PCCommandRequest(),
    db: Prisma = Depends(get_db),
):
    await _queue_pc_command(db, pc_id, "force_lock", {"reason": data.reason})
    return {"message": "Force lock queued"}


@router.post("/{pc_id}/commands/force-logout")
async def force_logout_pc(
    pc_id: int,
    data: PCCommandRequest = PCCommandRequest(),
    db: Prisma = Depends(get_db),
):
    from .sessions import _detach_session_from_pc, _active_remaining_minutes

    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    if pc.currentSessionId:
        session = await db.session.find_unique(where={"id": pc.currentSessionId})
        if session and session.isActive and session.status == "active":
            remaining = _active_remaining_minutes(session)
            await db.session.update(
                where={"id": session.id},
                data={
                    "status": "paused",
                    "pausedAt": datetime.now(timezone.utc),
                    "remainingMinutes": remaining,
                },
            )
            await _detach_session_from_pc(db, session)

    await _queue_pc_command(db, pc_id, "force_logout", {"reason": data.reason})
    return {"message": "Force logout queued"}


@router.post("/{pc_id}/commands/refresh-rules")
async def refresh_rules_pc(pc_id: int, db: Prisma = Depends(get_db)):
    await _queue_pc_command(db, pc_id, "refresh_rules")
    return {"message": "Refresh rules queued"}


@router.delete("/{pc_id}")
async def delete_pc(pc_id: int, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.delete(where={"id": pc_id})
    return {"detail": "PC deleted"}
