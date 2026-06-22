"""
Master Code API Routes
Handles generation, validation, and management of master codes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma
from shared.database import get_db
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import string
from shared.code_utils import normalize_master_code

router = APIRouter()


class MasterCodeGenerate(BaseModel):
    pc_id: int
    duration_minutes: int = 60


class MasterCodeResponse(BaseModel):
    id: int
    code: str
    pc_id: int
    duration_minutes: float
    is_used: bool
    used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MasterCodeValidate(BaseModel):
    code: str
    pc_id: int


class MasterCodeValidateResponse(BaseModel):
    success: bool
    message: str
    duration_minutes: Optional[float] = None
    session_token: Optional[str] = None


def generate_master_code() -> str:
    """Generate a unique master code."""
    # Format: XXXX-XXXX-XXXX (12 alphanumeric characters)
    chars = string.ascii_uppercase + string.digits
    code_parts = []
    for _ in range(3):
        part = ''.join(secrets.choice(chars) for _ in range(4))
        code_parts.append(part)
    return '-'.join(code_parts)


@router.post("/generate", response_model=MasterCodeResponse)
async def generate_code(
    data: MasterCodeGenerate,
    db: Prisma = Depends(get_db)
):
    """Generate a new master code for a specific PC."""
    # Verify PC exists
    pc = await db.pc.find_unique(where={"id": data.pc_id})
    if not pc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PC not found"
        )
    
    # Generate unique code
    code = generate_master_code()
    while await db.mastercode.find_unique(where={"code": code}):
        code = generate_master_code()
    
    # Create master code
    master_code = await db.mastercode.create(
        data={
            "code": code,
            "pcId": data.pc_id,
            "branchId": pc.branchId,
            "createdBy": 1,  # TODO: Get from auth
            "durationMinutes": data.duration_minutes,
            "expiresAt": datetime.utcnow() + timedelta(minutes=data.duration_minutes),
        }
    )
    
    return master_code


@router.post("/validate", response_model=MasterCodeValidateResponse)
async def validate_code(
    data: MasterCodeValidate,
    db: Prisma = Depends(get_db)
):
    """Validate a master code (called by client)."""
    code_value = normalize_master_code(data.code)
    if not code_value:
        return MasterCodeValidateResponse(
            success=False,
            message="Please enter a code",
        )

    master_code = await db.mastercode.find_unique(where={"code": code_value})
    
    if not master_code:
        return MasterCodeValidateResponse(
            success=False,
            message="Invalid code"
        )
    
    # Check if code is for this PC
    if master_code.pcId != data.pc_id:
        return MasterCodeValidateResponse(
            success=False,
            message="Invalid code for this PC"
        )
    
    # Check if code is already used
    if master_code.isUsed:
        return MasterCodeValidateResponse(
            success=False,
            message="Code already used"
        )
    
    # Check if code has expired
    if master_code.expiresAt and master_code.expiresAt < datetime.utcnow():
        return MasterCodeValidateResponse(
            success=False,
            message="Code has expired"
        )
    
    # Mark code as used
    await db.mastercode.update(
        where={"id": master_code.id},
        data={
            "isUsed": True,
            "usedAt": datetime.utcnow()
        }
    )
    
    # Reset wrong code attempts on PC
    await db.pc.update(
        where={"id": data.pc_id},
        data={"wrongCodeAttempts": 0}
    )
    
    return MasterCodeValidateResponse(
        success=True,
        message="Code validated successfully",
        duration_minutes=master_code.durationMinutes
    )


@router.get("/", response_model=List[MasterCodeResponse])
async def list_codes(
    pc_id: Optional[int] = None,
    db: Prisma = Depends(get_db)
):
    """List all master codes, optionally filtered by PC."""
    if pc_id:
        codes = await db.mastercode.find_many(
            where={"pcId": pc_id},
            order={"createdAt": "desc"}
        )
    else:
        codes = await db.mastercode.find_many(
            order={"createdAt": "desc"},
            take=100
        )
    return codes


@router.delete("/{code_id}")
async def revoke_code(
    code_id: int,
    db: Prisma = Depends(get_db)
):
    """Revoke/delete a master code."""
    code = await db.mastercode.find_unique(where={"id": code_id})
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code not found"
        )
    
    await db.mastercode.delete(where={"id": code_id})
    return {"message": "Code revoked"}


@router.get("/pc/{pc_id}")
async def get_pc_codes(
    pc_id: int,
    db: Prisma = Depends(get_db)
):
    """Get all codes for a specific PC."""
    codes = await db.mastercode.find_many(
        where={"pcId": pc_id},
        order={"createdAt": "desc"}
    )
    return codes
