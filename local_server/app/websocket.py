from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.pc_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Remove from PC connections
        for pc_id, conn in list(self.pc_connections.items()):
            if conn == websocket:
                del self.pc_connections[pc_id]
                break
    
    def connect_pc(self, pc_id: int, websocket: WebSocket):
        """Register a WebSocket connection for a specific PC."""
        self.pc_connections[pc_id] = websocket
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific connection."""
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connections."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass
    
    async def send_pc_update(self, pc_id: int, data: Dict[str, Any]):
        """Send update to PC-specific connection."""
        if pc_id in self.pc_connections:
            try:
                await self.pc_connections[pc_id].send_text(json.dumps(data))
            except Exception:
                pass
    
    async def broadcast_pc_status(self, pc_id: int, status: Dict[str, Any]):
        """Broadcast PC status update to all dashboard connections."""
        message = json.dumps({
            "type": "pc_status",
            "pc_id": pc_id,
            "data": status,
        })
        await self.broadcast(message)
    
    async def broadcast_session_update(self, session_data: Dict[str, Any]):
        """Broadcast session update to all dashboard connections."""
        message = json.dumps({
            "type": "session_update",
            "data": session_data,
        })
        await self.broadcast(message)
    
    async def broadcast_stats_update(self, stats: Dict[str, Any]):
        """Broadcast dashboard stats update."""
        message = json.dumps({
            "type": "stats_update",
            "data": stats,
        })
        await self.broadcast(message)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe_pc":
                pc_id = message.get("pc_id")
                if pc_id:
                    manager.connect_pc(pc_id, websocket)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "pc_id": pc_id,
                    }))
            
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
