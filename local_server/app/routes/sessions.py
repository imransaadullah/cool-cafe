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
from typing import Optional, List
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
    start_time: datetime
    end_time: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    total_paused_minutes: float
    duration_minutes: float
    remaining_minutes: Optional[float] = None
    status: str
    is_active: bool
    amount_charged: float
    created_at: datetime

    class Config:
        from_attributes = True


class HeartbeatResponse(BaseModel):
    status: str
    time_left: float
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
    action: Optional[str] = None


class ResumeInfoResponse(BaseModel):
    can_resume: bool
    message: Optional[str] = None
    session_id: Optional[int] = None
    remaining_minutes: Optional[float] = None
    remaining_seconds: Optional[float] = None
    resume_count: Optional[int] = None
    max_resumes: Optional[int] = None
    resumes_remaining: Optional[int] = None


class ResumeSessionResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[int] = None
    end_time: Optional[datetime] = None
    remaining_minutes: Optional[float] = None
    resume_count: Optional[int] = None
    max_resumes: Optional[int] = None
    resumes_remaining: Optional[int] = None


def _session_resume_count(session) -> int:
    return getattr(session, "resumeCount", None) or 0


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _forfeit_paused_session(db: Prisma, session, status: str = "forfeited"):
    """Close a paused session so a new code can be redeemed on this PC."""
    await db.session.update(
        where={"id": session.id},
        data={
            "status": status,
            "isActive": False,
            "endTime": utcnow(),
        },
    )
    await db.pc.update(
        where={"id": session.pcId},
        data={"currentSessionId": None, "status": "online"},
    )


def _build_resume_info(session) -> ResumeInfoResponse:
    remaining = session.remainingMinutes or 0
    max_res = max_allowed_resumes(session.durationMinutes)
    used = _session_resume_count(session)
    left = resumes_remaining(session.durationMinutes, used)

    if remaining < MIN_REMAINING_MINUTES_TO_RESUME:
        return ResumeInfoResponse(
            can_resume=False,
            message=f"Less than {MIN_REMAINING_MINUTES_TO_RESUME} minutes remaining",
            session_id=session.id,
            remaining_minutes=remaining,
            remaining_seconds=remaining * 60,
            resume_count=used,
            max_resumes=max_res,
            resumes_remaining=left,
        )

    if left <= 0:
        return ResumeInfoResponse(
            can_resume=False,
            message="No logins remaining for this session",
            session_id=session.id,
            remaining_minutes=remaining,
            remaining_seconds=remaining * 60,
            resume_count=used,
            max_resumes=max_res,
            resumes_remaining=0,
        )

    return ResumeInfoResponse(
        can_resume=True,
        session_id=session.id,
        remaining_minutes=remaining,
        remaining_seconds=remaining * 60,
        resume_count=used,
        max_resumes=max_res,
        resumes_remaining=left,
    )


async def _get_paused_session_for_pc(pc_id: int, db: Prisma):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        return None, pc

    if pc.currentSessionId:
        session = await db.session.find_unique(where={"id": pc.currentSessionId})
        if session and session.isActive and session.status == "paused":
            return session, pc

    session = await db.session.find_first(
        where={"pcId": pc_id, "isActive": True, "status": "paused"},
        order={"pausedAt": "desc"},
    )
    if session:
        if pc.currentSessionId != session.id:
            await db.pc.update(
                where={"id": pc_id},
                data={"currentSessionId": session.id},
            )
        return session, pc

    return None, pc


async def _resume_session_record(session, db: Prisma) -> ResumeSessionResponse:
    info = _build_resume_info(session)
    if not info.can_resume:
        return ResumeSessionResponse(success=False, message=info.message or "Cannot resume")

    remaining = session.remainingMinutes or 0
    total_paused = session.totalPausedMinutes or 0
    if session.pausedAt:
        paused_duration = (utcnow() - _ensure_utc(session.pausedAt)).total_seconds() / 60
        total_paused += paused_duration

    new_start_time = utcnow() - timedelta(minutes=session.durationMinutes - remaining)
    new_resume_count = _session_resume_count(session) + 1
    end_time = utcnow() + timedelta(minutes=remaining)

    await db.session.update(
        where={"id": session.id},
        data={
            "status": "active",
            "pausedAt": None,
            "totalPausedMinutes": total_paused,
            "startTime": new_start_time,
            "endTime": end_time,
            "resumeCount": new_resume_count,
        },
    )

    await db.pc.update(
        where={"id": session.pcId},
        data={"status": "in_use", "currentSessionId": session.id},
    )

    max_res = max_allowed_resumes(session.durationMinutes)
    left = resumes_remaining(session.durationMinutes, new_resume_count)

    return ResumeSessionResponse(
        success=True,
        message="Session resumed",
        session_id=session.id,
        end_time=end_time,
        remaining_minutes=remaining,
        resume_count=new_resume_count,
        max_resumes=max_res,
        resumes_remaining=left,
    )


@router.get("/pc/{pc_id}/resume-info", response_model=ResumeInfoResponse)
async def get_resume_info(pc_id: int, db: Prisma = Depends(get_db)):
    """Check whether this PC has a paused session that can be resumed."""
    session, _pc = await _get_paused_session_for_pc(pc_id, db)
    if not session:
        return ResumeInfoResponse(can_resume=False, message="No paused session")
    return _build_resume_info(session)


@router.post("/pc/{pc_id}/resume", response_model=ResumeSessionResponse)
async def resume_pc_session(pc_id: int, db: Prisma = Depends(get_db)):
    """Resume the paused session for this PC (no access code required)."""
    session, _pc = await _get_paused_session_for_pc(pc_id, db)
    if not session:
        return ResumeSessionResponse(success=False, message="No paused session")
    return await _resume_session_record(session, db)


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
    # Check if PC exists
    pc = await db.pc.find_unique(where={"id": session_data.pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    # Check if PC already has active session
    if pc.currentSessionId:
        existing = await db.session.find_unique(
            where={"id": pc.currentSessionId}
        )
        if existing and existing.isActive:
            raise HTTPException(status_code=400, detail="PC already has active session")
    
    # Validate code if provided
    code_id = None
    if session_data.code:
        code = await db.code.find_unique(where={"code": session_data.code})
        if not code or code.isUsed:
            raise HTTPException(status_code=400, detail="Invalid or used code")
        code_id = code.id
        # Mark code as used
        await db.code.update(
            where={"id": code.id},
            data={"isUsed": True, "usedAt": utcnow()},
        )
    
    # Create session
    session = await db.session.create(
        data={
            "pcId": session_data.pc_id,
            "branchId": session_data.branch_id,
            "codeId": code_id,
            "durationMinutes": session_data.duration_minutes,
            "localId": str(uuid.uuid4()),
            "startTime": utcnow(),
            "endTime": utcnow() + timedelta(minutes=session_data.duration_minutes),
        }
    )
    
    # Update PC
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
    
    # End session
    await db.session.update(
        where={"id": session_id},
        data={
            "endTime": utcnow(),
            "status": "completed",
            "isActive": False,
        },
    )
    
    # Update PC
    await db.pc.update(
        where={"id": session.pcId},
        data={"currentSessionId": None, "status": "online"},
    )
    
    return {"detail": "Session ended"}


@router.post("/pause")
async def pause_session(session_id: int, db: Prisma = Depends(get_db)):
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")
    
    # Calculate remaining time
    elapsed = (utcnow() - _ensure_utc(session.startTime)).total_seconds() / 60
    paused = session.totalPausedMinutes or 0
    remaining = session.durationMinutes - elapsed + paused

    if remaining < MIN_REMAINING_MINUTES_TO_RESUME:
        raise HTTPException(
            status_code=400,
            detail=f"Less than {MIN_REMAINING_MINUTES_TO_RESUME} minutes remaining, cannot pause",
        )
    
    # Pause session
    await db.session.update(
        where={"id": session_id},
        data={
            "status": "paused",
            "pausedAt": utcnow(),
            "remainingMinutes": remaining,
        },
    )
    
    # Update PC
    await db.pc.update(
        where={"id": session.pcId},
        data={"status": "online"},
    )
    
    return {"detail": "Session paused", "remaining_minutes": remaining}


@router.post("/resume", response_model=ResumeSessionResponse)
async def resume_session(session_id: int, db: Prisma = Depends(get_db)):
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "paused":
        raise HTTPException(status_code=400, detail="Session is not paused")

    return await _resume_session_record(session, db)


@router.get("/heartbeat/{pc_id}", response_model=HeartbeatResponse)
async def heartbeat(pc_id: int, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        return HeartbeatResponse(status="locked", time_left=0, is_active=False)
    
    # Update heartbeat time
    await db.pc.update(
        where={"id": pc_id},
        data={"lastHeartbeatAt": utcnow()},
    )
    
    if not pc.currentSessionId:
        return HeartbeatResponse(status="locked", time_left=0, is_active=False)
    
    session = await db.session.find_unique(where={"id": pc.currentSessionId})
    if not session or not session.isActive:
        return HeartbeatResponse(status="locked", time_left=0, is_active=False)
    
    if session.status == "paused":
        return HeartbeatResponse(
            status="paused",
            time_left=(session.remainingMinutes or 0) * 60,
            is_active=True,
            session_id=session.id,
        )
    
    # Calculate remaining time
    elapsed = (utcnow() - session.startTime).total_seconds() / 60
    paused = session.totalPausedMinutes or 0
    remaining = session.durationMinutes - elapsed + paused
    
    if remaining <= 0:
        # Session expired
        await db.session.update(
            where={"id": session.id},
            data={
                "status": "expired",
                "isActive": False,
                "endTime": utcnow(),
            },
        )
        await db.pc.update(
            where={"id": pc_id},
            data={"currentSessionId": None, "status": "online"},
        )
        return HeartbeatResponse(status="locked", time_left=0, is_active=False)
    
    return HeartbeatResponse(
        status="active",
        time_left=remaining * 60,
        is_active=True,
        session_id=session.id,
    )


@router.post("/redeem-code", response_model=CodeRedeemResponse)
async def redeem_code(request: CodeRedeemRequest, db: Prisma = Depends(get_db)):
    # Find code
    code = await db.code.find_unique(where={"code": request.code})
    if not code:
        return CodeRedeemResponse(success=False, message="Invalid code")

    # Check if PC exists
    pc = await db.pc.find_unique(where={"id": request.pc_id})
    if not pc:
        return CodeRedeemResponse(success=False, message="PC not found")

    if pc.currentSessionId:
        existing = await db.session.find_unique(where={"id": pc.currentSessionId})
        if existing and existing.isActive and existing.status == "active":
            return CodeRedeemResponse(
                success=False,
                message="PC already has an active session",
            )
        if existing and existing.isActive and existing.status == "paused":
            info = _build_resume_info(existing)
            same_code = code.isUsed and existing.codeId == code.id
            if same_code and info.can_resume:
                result = await _resume_session_record(existing, db)
                if result.success:
                    return CodeRedeemResponse(
                        success=True,
                        message="Session resumed",
                        session_id=result.session_id,
                        end_time=result.end_time,
                        duration_minutes=existing.durationMinutes,
                    )
                return CodeRedeemResponse(
                    success=False,
                    message=result.message or "Cannot resume session",
                    action="resume",
                    session_id=existing.id,
                )
            if not code.isUsed:
                await _forfeit_paused_session(db, existing)
                pc = await db.pc.find_unique(where={"id": request.pc_id})
            elif info.can_resume:
                return CodeRedeemResponse(
                    success=False,
                    message="Session paused — click Resume Session to continue",
                    action="resume",
                    session_id=existing.id,
                )
            elif (existing.remainingMinutes or 0) >= MIN_REMAINING_MINUTES_TO_RESUME:
                return CodeRedeemResponse(
                    success=False,
                    message=info.message or "Cannot start a new session yet",
                    action="resume",
                    session_id=existing.id,
                )

    if code.isUsed:
        paused_for_code = await db.session.find_first(
            where={
                "codeId": code.id,
                "pcId": request.pc_id,
                "isActive": True,
                "status": "paused",
            }
        )
        if paused_for_code:
            info = _build_resume_info(paused_for_code)
            if info.can_resume:
                await db.pc.update(
                    where={"id": request.pc_id},
                    data={"currentSessionId": paused_for_code.id},
                )
                result = await _resume_session_record(paused_for_code, db)
                if result.success:
                    return CodeRedeemResponse(
                        success=True,
                        message="Session resumed",
                        session_id=result.session_id,
                        end_time=result.end_time,
                        duration_minutes=paused_for_code.durationMinutes,
                    )
                return CodeRedeemResponse(
                    success=False,
                    message=result.message or "Cannot resume session",
                    action="resume",
                    session_id=paused_for_code.id,
                )
        return CodeRedeemResponse(success=False, message="Code already used")

    # Check if code is expired
    if code.expiresAt and code.expiresAt < utcnow():
        return CodeRedeemResponse(success=False, message="Code expired")
    
    # Mark code as used
    await db.code.update(
        where={"id": code.id},
        data={"isUsed": True, "usedAt": utcnow()},
    )
    
    # Create session
    session = await db.session.create(
        data={
            "pcId": request.pc_id,
            "branchId": code.branchId,
            "codeId": code.id,
            "durationMinutes": code.durationMinutes,
            "resumeCount": 0,
            "localId": str(uuid.uuid4()),
            "startTime": utcnow(),
            "endTime": utcnow() + timedelta(minutes=code.durationMinutes),
        }
    )
    
    # Update PC
    await db.pc.update(
        where={"id": request.pc_id},
        data={"currentSessionId": session.id, "status": "in_use"},
    )
    
    return CodeRedeemResponse(
        success=True,
        message="Code redeemed successfully",
        session_id=session.id,
        duration_minutes=code.durationMinutes,
        end_time=session.endTime,
    )
