"""WebSocket registration and pending command delivery for PC clients."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import WebSocket

from shared.database import db
from shared.pc_config import dump_pc_config, parse_pc_config, pop_pending_commands

from .client_config_builder import build_client_config


async def handle_client_register(pc_id: int, websocket: WebSocket, message: dict) -> None:
    prisma = db.get_client()
    pc = await prisma.pc.find_unique(where={"id": pc_id})
    if not pc:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "PC not found"})
        )
        return

    config = parse_pc_config(pc.config)
    pending = pop_pending_commands(config)
    client_config = await build_client_config(prisma, pc)

    status = "in_use" if message.get("session_active") else "online"
    await prisma.pc.update(
        where={"id": pc_id},
        data={
            "lastHeartbeatAt": datetime.now(timezone.utc),
            "clientRunning": True,
            "status": status,
            "config": dump_pc_config(config),
        },
    )

    await websocket.send_text(
        json.dumps(
            {
                "type": "registered",
                "pc_id": pc_id,
                "config_updates": client_config,
            }
        )
    )
    if pending:
        await websocket.send_text(
            json.dumps({"type": "commands", "commands": pending})
        )
