from fastapi import APIRouter, Depends, HTTPException
from prisma import Prisma
from shared.database import get_db
from shared.orm_model import ORMModel
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class FilterRuleCreate(BaseModel):
    branch_id: Optional[int] = None
    rule_type: str
    pattern: str
    action: str = "block"
    priority: int = 0
    description: Optional[str] = None


class FilterRuleUpdate(BaseModel):
    pattern: Optional[str] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class FilterRuleResponse(ORMModel):
    id: int
    branch_id: Optional[int] = None
    rule_type: str
    pattern: str
    action: str
    priority: int
    is_active: bool
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[FilterRuleResponse])
async def get_filter_rules(branch_id: int = None, db: Prisma = Depends(get_db)):
    where = {}
    if branch_id:
        where["branchId"] = branch_id
    
    rules = await db.filterrule.find_many(
        where=where,
        order={"priority": "desc"},
    )
    return rules


@router.post("/", response_model=FilterRuleResponse)
async def create_filter_rule(rule_data: FilterRuleCreate, db: Prisma = Depends(get_db)):
    rule = await db.filterrule.create(
        data={
            "branchId": rule_data.branch_id,
            "ruleType": rule_data.rule_type,
            "pattern": rule_data.pattern,
            "action": rule_data.action,
            "priority": rule_data.priority,
            "description": rule_data.description,
        }
    )
    return rule


@router.put("/{rule_id}", response_model=FilterRuleResponse)
async def update_filter_rule(
    rule_id: int, rule_data: FilterRuleUpdate, db: Prisma = Depends(get_db)
):
    rule = await db.filterrule.find_unique(where={"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = {}
    if rule_data.pattern is not None:
        update_data["pattern"] = rule_data.pattern
    if rule_data.action is not None:
        update_data["action"] = rule_data.action
    if rule_data.priority is not None:
        update_data["priority"] = rule_data.priority
    if rule_data.is_active is not None:
        update_data["isActive"] = rule_data.is_active
    if rule_data.description is not None:
        update_data["description"] = rule_data.description
    
    updated_rule = await db.filterrule.update(
        where={"id": rule_id},
        data=update_data,
    )
    return updated_rule


@router.delete("/{rule_id}")
async def delete_filter_rule(rule_id: int, db: Prisma = Depends(get_db)):
    rule = await db.filterrule.find_unique(where={"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.filterrule.delete(where={"id": rule_id})
    return {"detail": "Rule deleted"}
