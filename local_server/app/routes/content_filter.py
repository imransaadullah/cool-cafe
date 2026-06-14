"""
Content Filter API Routes
Used by clients to fetch and apply filtering rules
"""

from fastapi import APIRouter, Depends
from prisma import Prisma
from shared.database import get_db
from ..services.content_filter import content_filter
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()


class FilterStatus(BaseModel):
    dns_rules: int
    process_rules: int
    url_rules: int
    blocked_domains: int
    blocked_processes: int
    blocked_urls: int


class URLCheckRequest(BaseModel):
    url: str


class URLCheckResponse(BaseModel):
    url: str
    is_blocked: bool
    matched_rules: List[str]


@router.get("/status", response_model=FilterStatus)
async def get_filter_status(db: Prisma = Depends(get_db)):
    """Get current filter status."""
    return content_filter.get_status()


@router.get("/rules")
async def get_all_rules(branch_id: int = None, db: Prisma = Depends(get_db)):
    """Get filter rules, optionally scoped to a branch (+ global rules)."""
    where = {"isActive": True}
    if branch_id is not None:
        where = {
            "isActive": True,
            "OR": [
                {"branchId": branch_id},
                {"branchId": None},
            ],
        }

    rules = await db.filterrule.find_many(where=where)
    
    return {
        "dns": [
            {"pattern": r.pattern, "action": r.action}
            for r in rules if r.ruleType == "dns"
        ],
        "process": [
            {"pattern": r.pattern, "action": r.action}
            for r in rules if r.ruleType == "process"
        ],
        "url": [
            {"pattern": r.pattern, "action": r.action}
            for r in rules if r.ruleType == "url"
        ],
    }


@router.post("/apply")
async def apply_filters(db: Prisma = Depends(get_db)):
    """Apply all filter rules."""
    # Fetch rules from database
    rules = await db.filterrule.find_many(where={"isActive": True})
    
    rules_data = [
        {
            "rule_type": r.ruleType,
            "pattern": r.pattern,
            "action": r.action,
            "priority": r.priority,
        }
        for r in rules
    ]
    
    # Load and apply rules
    content_filter.load_rules(rules_data)
    content_filter.apply_all_rules()
    
    return {
        "success": True,
        "message": "Filters applied",
        "status": content_filter.get_status(),
    }


@router.post("/check-url", response_model=URLCheckResponse)
async def check_url(request: URLCheckRequest):
    """Check if a URL is blocked."""
    result = content_filter.url_filter.check_url(request.url)
    return result


@router.post("/block-domain")
async def block_domain(domain: str):
    """Block a specific domain."""
    content_filter.dns_filter.block_domain(domain)
    return {"success": True, "message": f"Domain {domain} blocked"}


@router.post("/unblock-domain")
async def unblock_domain(domain: str):
    """Unblock a specific domain."""
    content_filter.dns_filter.unblock_domain(domain)
    return {"success": True, "message": f"Domain {domain} unblocked"}


@router.post("/block-process")
async def block_process(process_name: str):
    """Block a specific process."""
    content_filter.process_filter.block_process(process_name)
    return {"success": True, "message": f"Process {process_name} blocked"}


@router.post("/unblock-process")
async def unblock_process(process_name: str):
    """Unblock a specific process."""
    content_filter.process_filter.unblock_process(process_name)
    return {"success": True, "message": f"Process {process_name} unblocked"}
