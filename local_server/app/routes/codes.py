from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from ..services.printer import code_printer
import random
import string
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


def generate_code(length: int = 8) -> str:
    """Generate a random alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


class CodeBatchCreate(BaseModel):
    branch_id: int
    count: int
    duration_minutes: float
    value_per_code: float = 0
    batch_name: Optional[str] = None


class CodeBatchResponse(ORMModel):
    id: int
    branch_id: int
    batch_name: Optional[str] = None
    count: int
    duration_minutes: float
    value_per_code: float
    is_active: bool
    printed: bool
    printed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CodeResponse(ORMModel):
    id: int
    code: str
    duration_minutes: float
    batch_id: Optional[int] = None
    branch_id: int
    is_used: bool
    used_at: Optional[datetime] = None
    value: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/batches", response_model=List[CodeBatchResponse])
async def get_batches(branch_id: int = None, db: Prisma = Depends(get_db)):
    where = {}
    if branch_id:
        where["branchId"] = branch_id
    
    batches = await db.codebatch.find_many(
        where=where,
        order={"createdAt": "desc"},
    )
    return batches


@router.get("/batches/{batch_id}", response_model=CodeBatchResponse)
async def get_batch(batch_id: int, db: Prisma = Depends(get_db)):
    batch = await db.codebatch.find_unique(where={"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@router.post("/batches", response_model=CodeBatchResponse)
async def create_batch(batch_data: CodeBatchCreate, db: Prisma = Depends(get_db)):
    # Create batch
    batch = await db.codebatch.create(
        data={
            "branchId": batch_data.branch_id,
            "count": batch_data.count,
            "durationMinutes": batch_data.duration_minutes,
            "valuePerCode": batch_data.value_per_code,
            "batchName": batch_data.batch_name,
        }
    )
    
    # Generate codes
    for _ in range(batch_data.count):
        while True:
            code_value = generate_code()
            existing = await db.code.find_unique(where={"code": code_value})
            if not existing:
                break
        
        await db.code.create(
            data={
                "code": code_value,
                "durationMinutes": batch_data.duration_minutes,
                "batchId": batch.id,
                "branchId": batch_data.branch_id,
                "value": batch_data.value_per_code,
            }
        )
    
    return batch


@router.get("/batches/{batch_id}/codes", response_model=List[CodeResponse])
async def get_batch_codes(batch_id: int, db: Prisma = Depends(get_db)):
    codes = await db.code.find_many(
        where={"batchId": batch_id},
    )
    return codes


@router.post("/batches/{batch_id}/print")
async def mark_batch_printed(batch_id: int, db: Prisma = Depends(get_db)):
    batch = await db.codebatch.find_unique(where={"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    await db.codebatch.update(
        where={"id": batch_id},
        data={"printed": True, "printedAt": datetime.utcnow()},
    )
    return {"detail": "Batch marked as printed"}


@router.get("/validate/{code}")
async def validate_code(code: str, db: Prisma = Depends(get_db)):
    code_obj = await db.code.find_unique(where={"code": code})
    if not code_obj:
        return {"valid": False, "message": "Invalid code"}
    
    if code_obj.isUsed:
        return {"valid": False, "message": "Code already used"}
    
    if code_obj.expiresAt and code_obj.expiresAt < datetime.now(timezone.utc):
        return {"valid": False, "message": "Code expired"}
    
    return {
        "valid": True,
        "duration_minutes": code_obj.durationMinutes,
        "value": code_obj.value,
    }


@router.get("/batches/{batch_id}/print-html")
async def print_batch_html(batch_id: int, db: Prisma = Depends(get_db)):
    """Generate printable HTML for a code batch."""
    batch = await db.codebatch.find_unique(where={"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    codes = await db.code.find_many(where={"batchId": batch_id})
    
    codes_data = [{"code": c.code, "duration_minutes": c.durationMinutes} for c in codes]
    batch_data = {
        "id": batch.id,
        "duration_minutes": batch.durationMinutes,
        "value_per_code": batch.valuePerCode,
    }
    
    html = code_printer.generate_html(codes_data, batch_data)
    
    return HTMLResponse(content=html)


@router.get("/batches/{batch_id}/print-text")
async def print_batch_text(batch_id: int, db: Prisma = Depends(get_db)):
    """Generate printable text for a code batch."""
    batch = await db.codebatch.find_unique(where={"id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    codes = await db.code.find_many(where={"batchId": batch_id})
    
    codes_data = [{"code": c.code, "duration_minutes": c.durationMinutes} for c in codes]
    batch_data = {
        "id": batch.id,
        "duration_minutes": batch.durationMinutes,
        "value_per_code": batch.valuePerCode,
    }
    
    text = code_printer.generate_text(codes_data, batch_data)
    
    return HTMLResponse(content=f"<pre>{text}</pre>")
