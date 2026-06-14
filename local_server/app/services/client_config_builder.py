"""Build merged client configuration from branch, PC, and filter rules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from prisma import Prisma

from shared.app_policy import merge_app_policy
from shared.pc_config import parse_pc_config


async def fetch_branch_filter_rules(db: Prisma, branch_id: int) -> List[Any]:
    return await db.filterrule.find_many(
        where={
            "isActive": True,
            "OR": [
                {"branchId": branch_id},
                {"branchId": None},
            ],
        },
        order={"priority": "desc"},
    )


async def build_client_config(db: Prisma, pc) -> Dict[str, Any]:
    branch = await db.branch.find_unique(where={"id": pc.branchId})
    branch_config = branch.config if branch and branch.config else {}
    pc_config = parse_pc_config(pc.config)
    filter_rules = await fetch_branch_filter_rules(db, pc.branchId)

    app_policy = merge_app_policy(branch_config, pc_config, filter_rules)

    branch_mode = None
    if isinstance(branch_config, dict):
        branch_mode = branch_config.get("client_mode")

    client_mode = pc_config.get("client_mode") or branch_mode or "production"

    dns_rules = [
        {"pattern": r.pattern, "action": r.action}
        for r in filter_rules
        if r.ruleType == "dns"
    ]
    url_rules = [
        {"pattern": r.pattern, "action": r.action}
        for r in filter_rules
        if r.ruleType == "url"
    ]

    return {
        "client_mode": client_mode,
        "app_policy": app_policy,
        "filtering": {
            "dns_blocking": True,
            "process_blocking": True,
            "url_filtering": bool(url_rules),
            "dns": dns_rules,
            "url": url_rules,
        },
        "security": {
            "alarm_enabled": pc.alarmEnabled,
            "alarm_color": pc.alarmColor or "#FF0000",
            "recovery_combo": pc.recoveryKeyCombo,
            "run_as_service": pc.runAsService,
        },
    }
