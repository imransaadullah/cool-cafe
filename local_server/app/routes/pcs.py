from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

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


@router.get("/", response_model=List[PCResponse])
async def get_pcs(branch_id: int = None, db: Prisma = Depends(get_db)):
    if branch_id:
        pcs = await db.pc.find_many(where={"branchId": branch_id})
    else:
        pcs = await db.pc.find_many()
    return pcs


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


@router.delete("/{pc_id}")
async def delete_pc(pc_id: int, db: Prisma = Depends(get_db)):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc:
        raise HTTPException(status_code=404, detail="PC not found")
    
    await db.pc.delete(where={"id": pc_id})
    return {"detail": "PC deleted"}
