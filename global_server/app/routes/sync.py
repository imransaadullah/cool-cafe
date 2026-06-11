from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter()


class SyncData(BaseModel):
    branch_id: int
    action_type: str
    table_name: str
    record_id: str
    payload: Dict[str, Any]


class SyncResponse(BaseModel):
    success: bool
    message: str
    records_synced: int


@router.post("/pull")
async def pull_sync_data(branch_id: int, db: Prisma = Depends(get_db)):
    """Pull latest data from global server for a branch."""
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    return {
        "branch": {
            "id": branch.id,
            "name": branch.name,
            "config": branch.config,
        },
        "sync_time": datetime.utcnow().isoformat(),
    }


@router.post("/push", response_model=SyncResponse)
async def push_sync_data(sync_data: SyncData, db: Prisma = Depends(get_db)):
    """Push data from local server to global server."""
    # Store in offline queue for processing
    queue_item = await db.offlinequeue.create(
        data={
            "actionType": sync_data.action_type,
            "tableName": sync_data.table_name,
            "recordId": sync_data.record_id,
            "payload": str(sync_data.payload),
            "synced": False,
        }
    )
    
    return SyncResponse(
        success=True,
        message="Data queued for sync",
        records_synced=1,
    )


@router.get("/status/{branch_id}")
async def get_sync_status(branch_id: int, db: Prisma = Depends(get_db)):
    """Get sync status for a branch."""
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Count pending sync items
    pending_count = await db.offlinequeue.count(
        where={"synced": False}
    )
    
    return {
        "branch_id": branch.id,
        "last_sync_at": branch.lastSyncAt,
        "pending_items": pending_count,
        "status": "synced" if pending_count == 0 else "pending",
    }


@router.post("/batch")
async def batch_sync(sync_items: List[SyncData], db: Prisma = Depends(get_db)):
    """Batch sync multiple items at once."""
    synced_count = 0
    
    for item in sync_items:
        await db.offlinequeue.create(
            data={
                "actionType": item.action_type,
                "tableName": item.table_name,
                "recordId": item.record_id,
                "payload": str(item.payload),
                "synced": False,
            }
        )
        synced_count += 1
    
    return {
        "success": True,
        "message": f"{synced_count} items queued for sync",
        "records_synced": synced_count,
    }
