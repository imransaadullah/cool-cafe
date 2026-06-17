from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from shared.session_rules import (
    MIN_REMAINING_MINUTES_TO_RESUME,
    max_allowed_resumes,
    resumes_remaining,
)
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, timezone
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


router = APIRouter()


class SessionCreate(BaseModel):
    pc_id: int
    branch_id: int
    duration_minutes: float
    code: Optional[str] = None
    code_id: Optional[int] = None


class SessionResponse(ORMModel):
    id: int
    pc_id: int
    branch_id: int
    code_id: Optional[int] = None
    current_pc_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    total_paused_minutes: float
    duration_minutes: float
    remaining_minutes: Optional[float] = None
    resume_count: Optional[int] = None
    status: str
    is_active: bool
    amount_charged: float
    created_at: datetime

    class Config:
        from_attributes = True


class AuthRequest(BaseModel):
    code: str
    pc_id: int


class AuthResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[int] = None
    duration_minutes: Optional[float] = None
    end_time: Optional[datetime] = None
    remaining_seconds: Optional[float] = None
    resume_count: Optional[int] = None
    max_resumes: Optional[int] = None
    resumes_remaining: Optional[int] = None
    action: Optional[str] = None


class LogoutRequest(BaseModel):
    code: str
    pc_id: int


class LogoutResponse(BaseModel):
    success: bool
    message: str
    remaining_minutes: Optional[float] = None


class SessionHeartbeatRequest(BaseModel):
    code: str
    pc_id: int


class SessionHeartbeatResponse(BaseModel):
    status: str
    remaining_seconds: float
    should_lock: bool
    session_id: Optional[int] = None


class ExtendSessionRequest(BaseModel):
    additional_minutes: float


class CodeRedeemRequest(BaseModel):
    code: str
    pc_id: int


class CodeRedeemResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[int] = None
    duration_minutes: Optional[float] = None
    end_time: Optional[datetime] = None
    action: Optional[str] = None


def _session_resume_count(session) -> int:
    return getattr(session, "resumeCount", None) or 0


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _active_remaining_minutes(session) -> float:
    elapsed = (utcnow() - _ensure_utc(session.startTime)).total_seconds() / 60
    paused = session.totalPausedMinutes or 0
    return session.durationMinutes - elapsed + paused


async def _get_session_for_code(code, db: Prisma):
    if code.activeSessionId:
        session = await db.session.find_unique(where={"id": code.activeSessionId})
        if session and session.isActive:
            return session
    return await db.session.find_first(
        where={"codeId": code.id, "isActive": True},
        order={"createdAt": "desc"},
    )


async def _clear_pc_session_ref(db: Prisma, pc_id: int):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if pc and pc.currentSessionId:
        await db.pc.update(
            where={"id": pc_id},
            data={"currentSessionId": None, "status": "online"},
        )


async def _attach_session_to_pc(db: Prisma, session, pc_id: int):
    await db.session.update(
        where={"id": session.id},
        data={"currentPcId": pc_id},
    )
    await db.pc.update(
        where={"id": pc_id},
        data={"currentSessionId": session.id, "status": "in_use"},
    )


async def _detach_session_from_pc(db: Prisma, session):
    pc_id = session.currentPcId
    await db.session.update(
        where={"id": session.id},
        data={"currentPcId": None},
    )
    if pc_id:
        pc = await db.pc.find_unique(where={"id": pc_id})
        if pc and pc.currentSessionId == session.id:
            await db.pc.update(
                where={"id": pc_id},
                data={"currentSessionId": None, "status": "online"},
            )


async def _close_session(db: Prisma, session, status: str = "completed"):
    await db.session.update(
        where={"id": session.id},
        data={
            "status": status,
            "isActive": False,
            "endTime": utcnow(),
            "currentPcId": None,
        },
    )
    if session.codeId:
        code = await db.code.find_unique(where={"id": session.codeId})
        if code and code.activeSessionId == session.id:
            await db.code.update(
                where={"id": code.id},
                data={"activeSessionId": None},
            )
    if session.currentPcId:
        await _clear_pc_session_ref(db, session.currentPcId)
    elif session.pcId:
        await _clear_pc_session_ref(db, session.pcId)


async def _forfeit_paused_session(db: Prisma, session, status: str = "forfeited"):
    await _close_session(db, session, status=status)


async def _find_active_session_on_pc(db: Prisma, pc_id: int):
    """Find the active session currently tied to a PC."""
    pc = await db.pc.find_unique(where={"id": pc_id})
    if pc and pc.currentSessionId:
        session = await db.session.find_unique(where={"id": pc.currentSessionId})
        if session and session.isActive and session.status == "active":
            return session

    return await db.session.find_first(
        where={
            "currentPcId": pc_id,
            "status": "active",
            "isActive": True,
        },
        order={"updatedAt": "desc"},
    )


async def _pause_active_session(
    db: Prisma,
    session,
    *,
    enforce_min_remaining: bool = True,
) -> float:
    """Pause an active session, store remaining time, and detach from its PC."""
    session = await db.session.find_unique(where={"id": session.id})
    if not session or not session.isActive or session.status != "active":
        raise HTTPException(status_code=400, detail="No active session to pause")

    remaining = max(0.0, _active_remaining_minutes(session))
    if enforce_min_remaining and remaining < MIN_REMAINING_MINUTES_TO_RESUME:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Less than {MIN_REMAINING_MINUTES_TO_RESUME} minutes remaining, "
                "cannot pause"
            ),
        )

    await db.session.update(
        where={"id": session.id},
        data={
            "status": "paused",
            "pausedAt": utcnow(),
            "remainingMinutes": remaining,
        },
    )
    await _detach_session_from_pc(db, session)
    return remaining


async def _resolve_pc_conflict(db: Prisma, pc, code, session_for_code):
    if not pc.currentSessionId:
        return None

    existing = await db.session.find_unique(where={"id": pc.currentSessionId})
    if not existing or not existing.isActive:
        return None

    if session_for_code and existing.id == session_for_code.id:
        return None

    if existing.status == "active":
        return AuthResponse(
            success=False,
            message="PC already has an active session",
        )

    if existing.status == "paused" and existing.codeId != code.id:
        await _forfeit_paused_session(db, existing)
        return None

    return None


def _login_quota_info(session):
    max_res = max_allowed_resumes(session.durationMinutes)
    used = _session_resume_count(session)
    left = resumes_remaining(session.durationMinutes, used)
    return max_res, used, left


def _can_resume_paused(session) -> Tuple[bool, str]:
    remaining = session.remainingMinutes or 0
    if remaining < MIN_REMAINING_MINUTES_TO_RESUME:
        return False, f"Less than {MIN_REMAINING_MINUTES_TO_RESUME} minutes remaining"

    _max_res, used, left = _login_quota_info(session)
    if left <= 0:
        return False, "No logins remaining for this ticket"
    return True, ""


async def _resume_paused_session(db: Prisma, session, pc_id: int) -> AuthResponse:
    session = await db.session.find_unique(where={"id": session.id})
    if not session or session.status != "paused":
        return AuthResponse(success=False, message="Session is not paused")

    can_resume, message = _can_resume_paused(session)
    if not can_resume:
        return AuthResponse(success=False, message=message, session_id=session.id)

    remaining = min(
        session.durationMinutes,
        max(0.0, session.remainingMinutes or 0),
    )
    total_paused = session.totalPausedMinutes or 0
    if session.pausedAt:
        paused_duration = (utcnow() - _ensure_utc(session.pausedAt)).total_seconds() / 60
        total_paused += paused_duration

    new_resume_count = _session_resume_count(session) + 1
    end_time = utcnow() + timedelta(minutes=remaining)
    new_start_time = utcnow() - timedelta(minutes=session.durationMinutes - remaining)

    await db.session.update(
        where={"id": session.id},
        data={
            "status": "active",
            "pausedAt": None,
            "totalPausedMinutes": total_paused,
            "startTime": new_start_time,
            "endTime": end_time,
            "resumeCount": new_resume_count,
            "pcId": pc_id,
        },
    )
    await _attach_session_to_pc(db, session, pc_id)

    max_res, used, left = _login_quota_info(session)
    return AuthResponse(
        success=True,
        message="Session resumed",
        session_id=session.id,
        duration_minutes=session.durationMinutes,
        end_time=end_time,
        remaining_seconds=remaining * 60,
        resume_count=new_resume_count,
        max_resumes=max_res,
        resumes_remaining=left,
    )


async def _create_new_session(db: Prisma, code, pc_id: int) -> AuthResponse:
    end_time = utcnow() + timedelta(minutes=code.durationMinutes)
    session = await db.session.create(
        data={
            "pcId": pc_id,
            "branchId": code.branchId,
            "codeId": code.id,
            "currentPcId": pc_id,
            "durationMinutes": code.durationMinutes,
            "resumeCount": 0,
            "localId": str(uuid.uuid4()),
            "startTime": utcnow(),
            "endTime": end_time,
        }
    )

    await db.code.update(
        where={"id": code.id},
        data={
            "isUsed": True,
            "usedAt": utcnow() if not code.usedAt else code.usedAt,
            "usedBySessionId": session.id,
            "activeSessionId": session.id,
        },
    )
    await db.pc.update(
        where={"id": pc_id},
        data={"currentSessionId": session.id, "status": "in_use"},
    )

    max_res = max_allowed_resumes(code.durationMinutes)
    return AuthResponse(
        success=True,
        message="Session started",
        session_id=session.id,
        duration_minutes=code.durationMinutes,
        end_time=end_time,
        remaining_seconds=code.durationMinutes * 60,
        resume_count=0,
        max_resumes=max_res,
        resumes_remaining=max_res,
    )


def _auth_success_from_active(session) -> AuthResponse:
    remaining = _active_remaining_minutes(session)
    max_res, used, left = _login_quota_info(session)
    return AuthResponse(
        success=True,
        message="Session active",
        session_id=session.id,
        duration_minutes=session.durationMinutes,
        end_time=session.endTime,
        remaining_seconds=max(0, remaining * 60),
        resume_count=used,
        max_resumes=max_res,
        resumes_remaining=left,
    )


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(request: AuthRequest, db: Prisma = Depends(get_db)):
    """Single entry point: start a new session or resume a paused ticket with code."""
    code = await db.code.find_unique(where={"code": request.code})
    if not code:
        return AuthResponse(success=False, message="Invalid code")
    if not code.isActive:
        return AuthResponse(success=False, message="Code is inactive")
    if code.expiresAt and _ensure_utc(code.expiresAt) < utcnow():
        return AuthResponse(success=False, message="Code expired")

    pc = await db.pc.find_unique(where={"id": request.pc_id})
    if not pc:
        return AuthResponse(success=False, message="PC not found")

    session = await _get_session_for_code(code, db)
    conflict = await _resolve_pc_conflict(db, pc, code, session)
    if conflict:
        return conflict

    if not session:
        if code.isUsed:
            return AuthResponse(success=False, message="Ticket finished or invalid")
        return await _create_new_session(db, code, request.pc_id)

    if session.status == "paused":
        return await _resume_paused_session(db, session, request.pc_id)

    if session.status == "active":
        if session.currentPcId is None:
            await _attach_session_to_pc(db, session, request.pc_id)
            return _auth_success_from_active(session)

        if session.currentPcId == request.pc_id:
            return _auth_success_from_active(session)

        other_pc = None
        if session.currentPcId:
            other_pc = await db.pc.find_unique(where={"id": session.currentPcId})
        pc_label = f"PC #{other_pc.pcNumber}" if other_pc else "another PC"
        return AuthResponse(
            success=False,
            message=f"Code in use on {pc_label} — logout there first",
        )

    await _close_session(db, session, status="expired")
    await db.code.update(where={"id": code.id}, data={"activeSessionId": None})
    return AuthResponse(success=False, message="Ticket expired or finished")


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest, db: Prisma = Depends(get_db)):
    """Pause the ticket session and detach it from this PC."""
    code = await db.code.find_unique(where={"code": request.code})
    if not code:
        return LogoutResponse(success=False, message="Invalid code")

    session = await _get_session_for_code(code, db)
    if not session or session.status != "active":
        return LogoutResponse(success=False, message="No active session for this code")
    if session.currentPcId != request.pc_id:
        return LogoutResponse(success=False, message="Session is not active on this PC")

    remaining = _active_remaining_minutes(session)
    if remaining < MIN_REMAINING_MINUTES_TO_RESUME:
        return LogoutResponse(
            success=False,
            message=f"Less than {MIN_REMAINING_MINUTES_TO_RESUME} minutes remaining, cannot logout",
        )

    try:
        remaining = await _pause_active_session(
            db,
            session,
            enforce_min_remaining=True,
        )
    except HTTPException as exc:
        return LogoutResponse(success=False, message=str(exc.detail))

    return LogoutResponse(
        success=True,
        message="Session paused",
        remaining_minutes=remaining,
    )


@router.post("/heartbeat", response_model=SessionHeartbeatResponse)
async def session_heartbeat(
    request: SessionHeartbeatRequest,
    db: Prisma = Depends(get_db),
):
    """Authoritative session timer — client must lock when should_lock is true."""
    code = await db.code.find_unique(where={"code": request.code})
    if not code:
        return SessionHeartbeatResponse(status="locked", remaining_seconds=0, should_lock=True)

    session = await _get_session_for_code(code, db)
    if not session or not session.isActive:
        return SessionHeartbeatResponse(status="locked", remaining_seconds=0, should_lock=True)

    if session.status == "paused" or session.currentPcId != request.pc_id:
        return SessionHeartbeatResponse(
            status="locked",
            remaining_seconds=0,
            should_lock=True,
            session_id=session.id,
        )

    remaining = _active_remaining_minutes(session)
    if remaining <= 0:
        await _close_session(db, session, status="expired")
        return SessionHeartbeatResponse(status="locked", remaining_seconds=0, should_lock=True)

    return SessionHeartbeatResponse(
        status="active",
        remaining_seconds=remaining * 60,
        should_lock=False,
        session_id=session.id,
    )


@router.get("/", response_model=List[SessionResponse])
async def get_sessions(
    branch_id: int = None,
    status: str = None,
    db: Prisma = Depends(get_db),
):
    where = {}
    if branch_id:
        where["branchId"] = branch_id
    if status:
        where["status"] = status

    sessions = await db.session.find_many(
        where=where,
        order={"createdAt": "desc"},
        take=100,
    )
    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int, db: Prisma = Depends(get_db)):
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/start", response_model=SessionResponse)
async def start_session(session_data: SessionCreate, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": session_data.pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")

    if pc.currentSessionId:
        existing = await db.session.find_unique(where={"id": pc.currentSessionId})
        if existing and existing.isActive and existing.status == "active":
            raise HTTPException(status_code=400, detail="PC already has active session")

    code_id = None
    if session_data.code:
        code = await db.code.find_unique(where={"code": session_data.code})
        if not code or not code.isActive:
            raise HTTPException(status_code=400, detail="Invalid code")
        code_id = code.id

    session = await db.session.create(
        data={
            "pcId": session_data.pc_id,
            "branchId": session_data.branch_id,
            "codeId": code_id,
            "currentPcId": session_data.pc_id,
            "durationMinutes": session_data.duration_minutes,
            "localId": str(uuid.uuid4()),
            "startTime": utcnow(),
            "endTime": utcnow() + timedelta(minutes=session_data.duration_minutes),
        }
    )

    if code_id:
        await db.code.update(
            where={"id": code_id},
            data={
                "isUsed": True,
                "usedAt": utcnow(),
                "activeSessionId": session.id,
            },
        )

    await db.pc.update(
        where={"id": session_data.pc_id},
        data={"currentSessionId": session.id, "status": "in_use"},
    )

    return session


@router.post("/stop")
async def stop_session(session_id: int, db: Prisma = Depends(get_db)):
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.isActive:
        raise HTTPException(status_code=400, detail="Session already ended")

    await _close_session(db, session, status="completed")
    return {"detail": "Session ended"}


@router.post("/resume", response_model=AuthResponse)
async def resume_session(session_id: int, db: Prisma = Depends(get_db)):
    """Admin: resume a paused session by id (attaches to session's pcId)."""
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "paused":
        raise HTTPException(status_code=400, detail="Session is not paused")

    pc_id = session.currentPcId or session.pcId
    return await _resume_paused_session(db, session, pc_id)


@router.post("/pause")
async def pause_session(session_id: int, db: Prisma = Depends(get_db)):
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    remaining = await _pause_active_session(
        db,
        session,
        enforce_min_remaining=True,
    )

    return {"detail": "Session paused", "remaining_minutes": remaining}


@router.post("/redeem-code", response_model=CodeRedeemResponse)
async def redeem_code(request: CodeRedeemRequest, db: Prisma = Depends(get_db)):
    """Backward-compatible alias for authenticate."""
    result = await authenticate(
        AuthRequest(code=request.code, pc_id=request.pc_id),
        db=db,
    )
    return CodeRedeemResponse(
        success=result.success,
        message=result.message,
        session_id=result.session_id,
        duration_minutes=result.duration_minutes,
        end_time=result.end_time,
        action=result.action,
    )


@router.post("/{session_id}/extend")
async def extend_session(
    session_id: int,
    request: ExtendSessionRequest,
    db: Prisma = Depends(get_db),
):
    """Admin: add time to an active session."""
    if request.additional_minutes <= 0:
        raise HTTPException(status_code=400, detail="additional_minutes must be positive")

    session = await db.session.find_unique(where={"id": session_id})
    if not session or not session.isActive:
        raise HTTPException(status_code=404, detail="Active session not found")

    new_duration = session.durationMinutes + request.additional_minutes
    await db.session.update(
        where={"id": session_id},
        data={"durationMinutes": new_duration},
    )

    if session.currentPcId:
        from .pcs import _queue_pc_command

        await _queue_pc_command(
            db,
            session.currentPcId,
            "extend",
            {"additional_minutes": request.additional_minutes},
        )

    return {
        "message": "Session extended",
        "session_id": session_id,
        "duration_minutes": new_duration,
        "additional_minutes": request.additional_minutes,
    }
