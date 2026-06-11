from fastapi import APIRouter, Depends
from prisma import Prisma
from shared.database import get_db
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class GlobalDashboard(BaseModel):
    total_branches: int
    active_branches: int
    total_admins: int
    branches_synced: int
    branches_pending: int


class BranchSummary(BaseModel):
    branch_id: int
    branch_name: str
    last_sync_at: Optional[str] = None
    status: str
    total_pcs: int = 0
    active_sessions: int = 0


@router.get("/overview", response_model=GlobalDashboard)
async def get_global_overview(db: Prisma = Depends(get_db)):
    """Get global dashboard overview."""
    total_branches = await db.branch.count()
    active_branches = await db.branch.count(where={"isActive": True})
    total_admins = await db.admin.count()
    
    # In a real implementation, we'd check sync status
    branches_synced = total_branches
    branches_pending = 0
    
    return GlobalDashboard(
        total_branches=total_branches,
        active_branches=active_branches,
        total_admins=total_admins,
        branches_synced=branches_synced,
        branches_pending=branches_pending,
    )


@router.get("/branches", response_model=List[BranchSummary])
async def get_branch_summaries(db: Prisma = Depends(get_db)):
    """Get summary for all branches."""
    branches = await db.branch.find_many()
    
    summaries = []
    for branch in branches:
        summaries.append(
            BranchSummary(
                branch_id=branch.id,
                branch_name=branch.name,
                last_sync_at=branch.lastSyncAt.isoformat()
                if branch.lastSyncAt
                else None,
                status="synced" if branch.lastSyncAt else "never_synced",
            )
        )
    
    return summaries
