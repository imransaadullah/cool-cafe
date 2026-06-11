from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
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
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


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
async def login(login_data: LoginRequest, db: Prisma = Depends(get_db)):
    try:
        logger.info(f"Login attempt for username: {login_data.username}")
        
        admin = await db.admin.find_unique(where={"username": login_data.username})
        
        if not admin:
            logger.warning(f"Admin not found: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
        
        logger.info(f"Admin found: {admin.username}, checking password...")
        
        if not verify_password(login_data.password, admin.passwordHash):
            logger.warning(f"Invalid password for: {login_data.username}")
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
        
        logger.info(f"Login successful for: {login_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


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
