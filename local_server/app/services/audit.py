"""
Audit Logging Service
Handles security audit logging for all events
"""

from prisma import Prisma
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import json


class AuditLogger:
    """Service for logging security audit events."""
    
    def __init__(self):
        self.client: Optional[Prisma] = None
    
    def connect(self, client: Prisma):
        """Set the Prisma client."""
        self.client = client
    
    async def log(
        self,
        event_type: str,
        branch_id: int,
        pc_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ):
        """Log a security audit event."""
        if not self.client:
            raise RuntimeError("AuditLogger not connected")
        
        await self.client.securityauditlog.create(
            data={
                "pcId": pc_id,
                "branchId": branch_id,
                "eventType": event_type,
                "details": json.dumps(details) if details else None,
                "ipAddress": ip_address,
            }
        )
    
    async def log_heartbeat(self, pc_id: int, branch_id: int, status: str):
        """Log client heartbeat."""
        await self.log(
            event_type="heartbeat",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"status": status},
        )
    
    async def log_master_code_used(self, pc_id: int, branch_id: int, code: str, online: bool):
        """Log master code usage."""
        await self.log(
            event_type="master_code_used",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"code": code[:4] + "****", "online": online},
        )
    
    async def log_static_code_used(self, pc_id: int, branch_id: int):
        """Log static code usage (offline)."""
        await self.log(
            event_type="static_code_used",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"offline": True},
        )
    
    async def log_wrong_code_attempt(self, pc_id: int, branch_id: int, attempt_count: int):
        """Log wrong code attempt."""
        await self.log(
            event_type="wrong_code_attempt",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"attempt_count": attempt_count},
        )
    
    async def log_alarm_triggered(self, pc_id: int, branch_id: int, reason: str):
        """Log alarm trigger."""
        await self.log(
            event_type="alarm_triggered",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"reason": reason},
        )
    
    async def log_bypass_attempt(self, pc_id: int, branch_id: int, method: str):
        """Log bypass attempt (task manager, uninstall, etc.)."""
        await self.log(
            event_type="bypass_attempt",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"method": method},
        )
    
    async def log_pc_banned(self, pc_id: int, branch_id: int, reason: Optional[str] = None):
        """Log PC ban."""
        await self.log(
            event_type="pc_banned",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"reason": reason} if reason else None,
        )
    
    async def log_pc_unbanned(self, pc_id: int, branch_id: int):
        """Log PC unban."""
        await self.log(
            event_type="pc_unbanned",
            pc_id=pc_id,
            branch_id=branch_id,
        )
    
    async def log_static_code_registered(self, pc_id: int, branch_id: int, recovery_combo: str):
        """Log static code registration."""
        await self.log(
            event_type="static_code_registered",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"recovery_combo": recovery_combo},
        )
    
    async def log_client_installed(self, pc_id: int, branch_id: int, version: str):
        """Log client installation."""
        await self.log(
            event_type="client_installed",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"version": version},
        )
    
    async def log_client_updated(self, pc_id: int, branch_id: int, old_version: str, new_version: str):
        """Log client update."""
        await self.log(
            event_type="client_updated",
            pc_id=pc_id,
            branch_id=branch_id,
            details={"old_version": old_version, "new_version": new_version},
        )


# Global audit logger instance
audit_logger = AuditLogger()
