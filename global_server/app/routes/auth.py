from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from shared.utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from shared.config import settings

router = APIRouter()


class AdminCreate(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    role: str = "branch_admin"
    branch_id: Optional[int] = None


class AdminResponse(ORMModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    branch_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/login", response_model=Token)
async def login(username: str, password: str, db: Prisma = Depends(get_db)):
    admin = await db.admin.find_unique(where={"username": username})
    if not admin or not verify_password(password, admin.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not admin.isActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Update last login
    await db.admin.update(
        where={"id": admin.id},
        data={"lastLoginAt": datetime.utcnow()},
    )
    
    access_token = create_access_token(
        data={"sub": admin.username, "role": admin.role, "branchId": admin.branchId},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/create", response_model=AdminResponse)
async def create_admin(admin_data: AdminCreate, db: Prisma = Depends(get_db)):
    # Check if username exists
    existing = await db.admin.find_unique(where={"username": admin_data.username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    # Create admin
    admin = await db.admin.create(
        data={
            "username": admin_data.username,
            "email": admin_data.email,
            "fullName": admin_data.full_name,
            "role": admin_data.role,
            "branchId": admin_data.branch_id,
            "passwordHash": get_password_hash(admin_data.password),
        }
    )
    return admin


@router.get("/me", response_model=AdminResponse)
async def get_current_user(username: str, db: Prisma = Depends(get_db)):
    admin = await db.admin.find_unique(where={"username": username})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin
