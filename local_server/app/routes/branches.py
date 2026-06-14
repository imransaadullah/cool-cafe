from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from shared.utils.auth import get_password_hash

router = APIRouter()


class BranchCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    client_mode: Optional[str] = None
    app_policy: Optional[dict] = None


class BranchResponse(ORMModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    last_sync_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


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


class BranchAdminCreate(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str


@router.get("/", response_model=List[BranchResponse])
async def get_branches(db: Prisma = Depends(get_db)):
    return await db.branch.find_many()


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(branch_id: int, db: Prisma = Depends(get_db)):
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.post("/", response_model=BranchResponse)
async def create_branch(branch_data: BranchCreate, db: Prisma = Depends(get_db)):
    branch = await db.branch.create(
        data={
            "name": branch_data.name,
            "address": branch_data.address,
            "phone": branch_data.phone,
            "email": branch_data.email,
        }
    )
    return branch


@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int, branch_data: BranchUpdate, db: Prisma = Depends(get_db)
):
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    update_data = {}
    if branch_data.name is not None:
        update_data["name"] = branch_data.name
    if branch_data.address is not None:
        update_data["address"] = branch_data.address
    if branch_data.phone is not None:
        update_data["phone"] = branch_data.phone
    if branch_data.email is not None:
        update_data["email"] = branch_data.email
    if branch_data.is_active is not None:
        update_data["isActive"] = branch_data.is_active

    if branch_data.client_mode is not None or branch_data.app_policy is not None:
        config = branch.config if isinstance(branch.config, dict) else {}
        if branch_data.client_mode is not None:
            config["client_mode"] = branch_data.client_mode
        if branch_data.app_policy is not None:
            existing = config.get("app_policy", {})
            if not isinstance(existing, dict):
                existing = {}
            existing.update(branch_data.app_policy)
            config["app_policy"] = existing
        update_data["config"] = config
    
    updated_branch = await db.branch.update(
        where={"id": branch_id},
        data=update_data,
    )
    return updated_branch


@router.get("/{branch_id}/app-policy")
async def get_branch_app_policy(branch_id: int, db: Prisma = Depends(get_db)):
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    config = branch.config if isinstance(branch.config, dict) else {}
    return {
        "client_mode": config.get("client_mode", "production"),
        "app_policy": config.get("app_policy", {}),
    }


@router.put("/{branch_id}/app-policy")
async def update_branch_app_policy(
    branch_id: int,
    data: BranchUpdate,
    db: Prisma = Depends(get_db),
):
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    config = branch.config if isinstance(branch.config, dict) else {}
    if data.client_mode is not None:
        config["client_mode"] = data.client_mode
    if data.app_policy is not None:
        existing = config.get("app_policy", {})
        if not isinstance(existing, dict):
            existing = {}
        existing.update(data.app_policy)
        config["app_policy"] = existing

    await db.branch.update(where={"id": branch_id}, data={"config": config})
    return {"message": "Branch app policy updated", "config": config}


@router.post("/{branch_id}/admins", response_model=AdminResponse)
async def create_branch_admin(
    branch_id: int, admin_data: BranchAdminCreate, db: Prisma = Depends(get_db)
):
    # Check if branch exists
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if username exists
    existing = await db.admin.find_unique(where={"username": admin_data.username})
    if existing:
        raise HTTPException(
            status_code=400, detail="Username already exists"
        )
    
    # Create admin
    admin = await db.admin.create(
        data={
            "username": admin_data.username,
            "email": admin_data.email,
            "fullName": admin_data.full_name,
            "role": "branch_admin",
            "branchId": branch_id,
            "passwordHash": get_password_hash(admin_data.password),
        }
    )
    return admin


@router.get("/{branch_id}/admins", response_model=List[AdminResponse])
async def get_branch_admins(branch_id: int, db: Prisma = Depends(get_db)):
    return await db.admin.find_many(where={"branchId": branch_id})


@router.delete("/{branch_id}")
async def delete_branch(branch_id: int, db: Prisma = Depends(get_db)):
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    await db.branch.delete(where={"id": branch_id})
    return {"detail": "Branch deleted"}
