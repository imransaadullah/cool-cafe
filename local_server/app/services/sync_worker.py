"""Background sync worker: push local offline queue to global server."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from prisma import Prisma
from shared.config import settings

logger = logging.getLogger(__name__)

_worker_task: Optional[asyncio.Task] = None


async def _push_item(client: httpx.AsyncClient, item: Any) -> bool:
    try:
        payload = json.loads(item.payload) if isinstance(item.payload, str) else item.payload
    except json.JSONDecodeError:
        payload = {"raw": item.payload}

    response = await client.post(
        "/api/sync/apply",
        json={
            "action_type": item.actionType,
            "table_name": item.tableName,
            "record_id": item.recordId,
            "payload": payload,
        },
        timeout=30.0,
    )
    return response.status_code == 200


async def sync_once(db: Prisma) -> int:
    """Push pending offline queue items to global server. Returns count synced."""
    if not settings.GLOBAL_SERVER_URL or not settings.SYNC_ENABLED:
        return 0

    pending = await db.offlinequeue.find_many(
        where={"synced": False},
        order={"createdAt": "asc"},
        take=50,
    )
    if not pending:
        return 0

    base = settings.GLOBAL_SERVER_URL.rstrip("/")
    synced = 0

    async with httpx.AsyncClient(base_url=base) as client:
        for item in pending:
            try:
                ok = await _push_item(client, item)
                if ok:
                    await db.offlinequeue.update(
                        where={"id": item.id},
                        data={"synced": True, "syncedAt": datetime.utcnow()},
                    )
                    synced += 1
                else:
                    await db.offlinequeue.update(
                        where={"id": item.id},
                        data={
                            "retryCount": item.retryCount + 1,
                            "errorMessage": "Global server rejected item",
                        },
                    )
            except Exception as exc:
                logger.warning("Sync push failed for item %s: %s", item.id, exc)
                await db.offlinequeue.update(
                    where={"id": item.id},
                    data={
                        "retryCount": item.retryCount + 1,
                        "errorMessage": str(exc)[:500],
                    },
                )

    if synced and settings.BRANCH_ID:
        await db.branch.update(
            where={"id": settings.BRANCH_ID},
            data={"lastSyncAt": datetime.utcnow()},
        )

    return synced


async def _worker_loop(db: Prisma):
    interval = max(1, settings.SYNC_INTERVAL_MINUTES) * 60
    while True:
        try:
            count = await sync_once(db)
            if count:
                logger.info("Synced %s items to global server", count)
        except Exception as exc:
            logger.error("Sync worker error: %s", exc)
        await asyncio.sleep(interval)


async def queue_sync_event(
    db: Prisma,
    action_type: str,
    table_name: str,
    record_id: str,
    payload: Dict[str, Any],
):
    """Enqueue a record for global sync."""
    if not settings.SYNC_ENABLED:
        return
    await db.offlinequeue.create(
        data={
            "actionType": action_type,
            "tableName": table_name,
            "recordId": record_id,
            "payload": json.dumps(payload),
            "synced": False,
        }
    )


def start_sync_worker(db: Prisma):
    global _worker_task
    if not settings.GLOBAL_SERVER_URL or not settings.SYNC_ENABLED:
        logger.info("Global sync worker disabled (no GLOBAL_SERVER_URL)")
        return
    if _worker_task and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_worker_loop(db))
    logger.info("Global sync worker started (interval %s min)", settings.SYNC_INTERVAL_MINUTES)


def stop_sync_worker():
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
    _worker_task = None
