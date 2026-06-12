#!/usr/bin/env python3
"""Auth-flow checks for code-centric sessions (runs against DB via route handlers)."""

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prisma import Prisma
from local_server.app.routes.sessions import (
    AuthRequest,
    LogoutRequest,
    SessionHeartbeatRequest,
    authenticate,
    logout,
    session_heartbeat,
)


async def create_code(db: Prisma, minutes: float = 30) -> str:
    batch = await db.codebatch.create(
        data={
            "branchId": 1,
            "durationMinutes": minutes,
            "count": 1,
            "valuePerCode": 100,
        }
    )
    code_str = f"TST{uuid.uuid4().hex[:6].upper()}"
    await db.code.create(
        data={
            "code": code_str,
            "durationMinutes": minutes,
            "batchId": batch.id,
            "branchId": 1,
            "value": 100,
        }
    )
    return code_str


async def cleanup_pc(db: Prisma, pc_id: int):
    pc = await db.pc.find_unique(where={"id": pc_id})
    if not pc or not pc.currentSessionId:
        return
    session = await db.session.find_unique(where={"id": pc.currentSessionId})
    if session and session.isActive:
        await db.session.update(
            where={"id": session.id},
            data={
                "status": "forfeited",
                "isActive": False,
                "endTime": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ),
                "currentPcId": None,
            },
        )
        if session.codeId:
            code = await db.code.find_unique(where={"id": session.codeId})
            if code and code.activeSessionId == session.id:
                await db.code.update(
                    where={"id": code.id},
                    data={"activeSessionId": None},
                )
    await db.pc.update(
        where={"id": pc_id},
        data={"currentSessionId": None, "status": "online"},
    )


async def ensure_pc(db: Prisma, number: int) -> int:
    existing = await db.pc.find_first(
        where={"branchId": 1, "pcNumber": number},
    )
    if existing:
        return existing.id
    pc = await db.pc.create(
        data={
            "name": f"AuthTest-{number}",
            "pcNumber": number,
            "branchId": 1,
        }
    )
    return pc.id


async def run_matrix():
    db = Prisma()
    await db.connect()

    pc1 = await ensure_pc(db, 301)
    pc2 = await ensure_pc(db, 302)
    await cleanup_pc(db, pc1)
    await cleanup_pc(db, pc2)

    # Same-PC resume (30 min ticket = 1 re-login)
    code_same_pc = await create_code(db, 30)
    print(f"Same-PC code: {code_same_pc}  PC1={pc1}\n")

    checks = []

    r = await authenticate(AuthRequest(code=code_same_pc, pc_id=pc1), db=db)
    checks.append(("new code on PC1", r.success, r.message))

    r = await logout(LogoutRequest(code=code_same_pc, pc_id=pc1), db=db)
    checks.append(("logout on PC1", r.success, r.message))

    r = await authenticate(AuthRequest(code=code_same_pc, pc_id=pc1), db=db)
    checks.append(("same-PC resume with code", r.success, r.message))

    r = await logout(LogoutRequest(code=code_same_pc, pc_id=pc1), db=db)
    checks.append(("cleanup same-PC session", r.success, r.message))

    # PC transfer (60 min ticket = 2 re-logins)
    code_transfer = await create_code(db, 60)
    print(f"Transfer code: {code_transfer}  PC1={pc1}  PC2={pc2}\n")

    r = await authenticate(AuthRequest(code=code_transfer, pc_id=pc1), db=db)
    checks.append(("transfer: start on PC1", r.success, r.message))

    r = await authenticate(AuthRequest(code=code_transfer, pc_id=pc2), db=db)
    checks.append((
        "transfer: block on PC2 without logout",
        not r.success and "logout" in (r.message or "").lower(),
        r.message,
    ))

    r = await logout(LogoutRequest(code=code_transfer, pc_id=pc1), db=db)
    checks.append(("transfer: logout PC1", r.success, r.message))

    r = await authenticate(AuthRequest(code=code_transfer, pc_id=pc2), db=db)
    checks.append(("transfer: resume on PC2", r.success, r.message))

    r = await session_heartbeat(
        SessionHeartbeatRequest(code=code_transfer, pc_id=pc2),
        db=db,
    )
    checks.append((
        "transfer: heartbeat on PC2",
        not r.should_lock and r.remaining_seconds > 0,
        f"remaining={r.remaining_seconds}",
    ))

    failed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{status}] {name}: {detail}")

    await db.disconnect()
    print()
    if failed:
        print(f"{failed} check(s) failed")
        sys.exit(1)
    print("All checks passed")


def main():
    print("Code-centric session auth test matrix\n")
    asyncio.run(run_matrix())


if __name__ == "__main__":
    main()
