from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import json
import logging

from .services.client_realtime import handle_client_register

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket connections: PC clients vs dashboard subscribers."""

    def __init__(self):
        self.dashboard_connections: List[WebSocket] = []
        self.client_connections: Dict[int, WebSocket] = {}

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> Optional[int]:
        disconnected_pc_id: Optional[int] = None
        if websocket in self.dashboard_connections:
            self.dashboard_connections.remove(websocket)
        for pc_id, conn in list(self.client_connections.items()):
            if conn is websocket:
                del self.client_connections[pc_id]
                disconnected_pc_id = pc_id
                break
        return disconnected_pc_id

    def connect_client(self, pc_id: int, websocket: WebSocket):
        existing = self.client_connections.get(pc_id)
        if existing and existing is not websocket:
            logger.info("Replacing stale WebSocket for PC %s", pc_id)
        self.client_connections[pc_id] = websocket

    def is_client_connected(self, pc_id: int) -> bool:
        return pc_id in self.client_connections

    async def _send_json(self, websocket: WebSocket, payload: Dict[str, Any]) -> bool:
        try:
            await websocket.send_text(json.dumps(payload))
            return True
        except Exception as exc:
            logger.debug("WebSocket send failed: %s", exc)
            return False

    async def send_client_commands(self, pc_id: int, commands: List[Dict[str, Any]]) -> bool:
        """Push commands to a connected PC client immediately."""
        if not commands:
            return False
        websocket = self.client_connections.get(pc_id)
        if not websocket:
            return False
        return await self._send_json(
            websocket,
            {"type": "commands", "commands": commands},
        )

    async def send_client_config(self, pc_id: int, config_updates: Dict[str, Any]) -> bool:
        websocket = self.client_connections.get(pc_id)
        if not websocket:
            return False
        return await self._send_json(
            websocket,
            {"type": "config_update", "config_updates": config_updates},
        )

    async def broadcast(self, message: str):
        dead: List[WebSocket] = []
        for connection in self.dashboard_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)

    async def broadcast_pc_status(self, pc_id: int, status: Dict[str, Any]):
        message = json.dumps(
            {
                "type": "pc_status",
                "pc_id": pc_id,
                "data": status,
            }
        )
        await self.broadcast(message)

    async def broadcast_session_update(self, session_data: Dict[str, Any]):
        message = json.dumps(
            {
                "type": "session_update",
                "data": session_data,
            }
        )
        await self.broadcast(message)

    async def broadcast_stats_update(self, stats: Dict[str, Any]):
        message = json.dumps(
            {
                "type": "stats_update",
                "data": stats,
            }
        )
        await self.broadcast(message)


manager = ConnectionManager()


async def mark_client_offline(pc_id: int) -> None:
    try:
        from shared.database import db

        prisma = db.get_client()
        await prisma.pc.update(
            where={"id": pc_id},
            data={"clientRunning": False, "status": "offline"},
        )
        await manager.broadcast_pc_status(
            pc_id,
            {"client_running": False, "status": "offline"},
        )
    except Exception as exc:
        logger.debug("Could not mark PC %s offline: %s", pc_id, exc)


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboard subscribers and PC clients."""
    await manager.connect_dashboard(websocket)
    role: Optional[str] = None

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "client_register":
                pc_id = message.get("pc_id")
                if pc_id:
                    role = "client"
                    manager.connect_client(int(pc_id), websocket)
                    await handle_client_register(int(pc_id), websocket, message)

            elif msg_type == "dashboard_register":
                role = "dashboard"
                await websocket.send_text(json.dumps({"type": "registered", "role": "dashboard"}))

            elif msg_type == "subscribe_pc":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "subscribed",
                            "pc_id": message.get("pc_id"),
                        }
                    )
                )

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pc_id = manager.disconnect(websocket)
        if pc_id is not None:
            await mark_client_offline(pc_id)
    except Exception as exc:
        logger.warning("WebSocket error (%s): %s", role, exc)
        pc_id = manager.disconnect(websocket)
        if pc_id is not None:
            await mark_client_offline(pc_id)
