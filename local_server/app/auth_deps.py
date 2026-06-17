"""JWT authentication dependencies for admin routes."""

from __future__ import annotations

import re
from typing import Optional, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prisma import Prisma
from shared.database import get_db
from shared.utils.auth import decode_access_token

security = HTTPBearer(auto_error=False)

# Client-facing mutating endpoints that must stay unauthenticated.
_EXEMPT_PATTERNS = [
    re.compile(r"^/api/auth/login$"),
    re.compile(r"^/api/auth/create$"),
    re.compile(r"^/api/pcs/register$"),
    re.compile(r"^/api/pcs/\d+/heartbeat$"),
    re.compile(r"^/api/pcs/\d+/register-static-code$"),
    re.compile(r"^/api/pcs/\d+/report-alarm$"),
    re.compile(r"^/api/pcs/\d+/report-bypass$"),
    re.compile(r"^/api/pcs/\d+/apps/inventory$"),
    re.compile(r"^/api/sessions/authenticate$"),
    re.compile(r"^/api/sessions/logout$"),
    re.compile(r"^/api/sessions/heartbeat$"),
    re.compile(r"^/api/sessions/start$"),
    re.compile(r"^/api/sessions/stop$"),
    re.compile(r"^/api/sessions/resume$"),
    re.compile(r"^/api/sessions/pause$"),
    re.compile(r"^/api/sessions/redeem-code$"),
    re.compile(r"^/api/master-codes/validate$"),
    re.compile(r"^/api/webhooks/"),
    re.compile(r"^/api/health$"),
    re.compile(r"^/ws$"),
]

READ_ONLY_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS"}


def is_exempt_path(method: str, path: str) -> bool:
    if method in READ_ONLY_METHODS:
        return True
    for pattern in _EXEMPT_PATTERNS:
        if pattern.match(path):
            return True
    return False


class AdminUser:
    def __init__(self, username: str, role: str, branch_id: Optional[int]):
        self.username = username
        self.role = role
        self.branch_id = branch_id

    def has_role(self, *roles: str) -> bool:
        if self.role == "owner":
            return True
        return self.role in roles


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Prisma = Depends(get_db),
) -> AdminUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    admin = await db.admin.find_unique(where={"username": payload["sub"]})
    if not admin or not admin.isActive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    return AdminUser(
        username=admin.username,
        role=admin.role,
        branch_id=admin.branchId,
    )


def require_roles(*roles: str):
    async def checker(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        if not admin.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return admin

    return checker


async def enforce_admin_auth(request: Request, call_next):
    """Middleware helper: block unauthenticated mutating admin requests."""
    if is_exempt_path(request.method, request.url.path):
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth[7:]
    payload = decode_access_token(token)
    if not payload:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )

    request.state.admin_username = payload.get("sub")
    request.state.admin_role = payload.get("role")
    return await call_next(request)
