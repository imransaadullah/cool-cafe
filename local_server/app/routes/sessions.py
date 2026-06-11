from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
import uuid

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
    elapsed = (utcnow() - session.startTime).total_seconds() / 60
    paused = session.totalPausedMinutes or 0
    remaining = session.durationMinutes - elapsed + paused
    
    if remaining < 5:
        raise HTTPException(status_code=400, detail="Less than 5 minutes remaining, cannot pause")
    
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


@router.post("/resume")
async def resume_session(session_id: int, db: Prisma = Depends(get_db)):
    session = await db.session.find_unique(where={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != "paused":
        raise HTTPException(status_code=400, detail="Session is not paused")
    
    # Calculate paused duration
    total_paused = session.totalPausedMinutes or 0
    if session.pausedAt:
        paused_duration = (utcnow() - session.pausedAt).total_seconds() / 60
        total_paused += paused_duration
    
    # Resume session
    new_start_time = utcnow() - timedelta(
        minutes=session.durationMinutes - (session.remainingMinutes or 0)
    )
    
    await db.session.update(
        where={"id": session_id},
        data={
            "status": "active",
            "pausedAt": None,
            "totalPausedMinutes": total_paused,
            "startTime": new_start_time,
        },
    )
    
    # Update PC
    await db.pc.update(
        where={"id": session.pcId},
        data={"status": "in_use"},
    )
    
    return {"detail": "Session resumed"}


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
    
    if code.isUsed:
        return CodeRedeemResponse(success=False, message="Code already used")
    
    # Check if code is expired
    if code.expiresAt and code.expiresAt < utcnow():
        return CodeRedeemResponse(success=False, message="Code expired")
    
    # Check if PC exists
    pc = await db.pc.find_unique(where={"id": request.pc_id})
    if not pc:
        return CodeRedeemResponse(success=False, message="PC not found")
    
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
