"""WebSocket client for instant server commands and offline detection."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional
from urllib.parse import urlparse

from PyQt6.QtCore import QThread, pyqtSignal

from services.config_manager import client_config

logger = logging.getLogger(__name__)

try:
    import websocket

    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False


def http_to_ws_url(server_url: str) -> str:
    parsed = urlparse(server_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    host = parsed.netloc or parsed.path
    return f"{scheme}://{host}/ws"


class RealtimeThread(QThread):
    """Maintains a WebSocket to the server for push commands and fast offline detection."""

    command_signal = pyqtSignal(list)
    config_update = pyqtSignal(dict)
    server_offline = pyqtSignal()
    server_online = pyqtSignal()

    def __init__(self, pc_id: int, server_url: str | None = None):
        super().__init__()
        self.pc_id = pc_id
        self.server_url = server_url or client_config.get_server_url()
        self.running = True
        self._connected = False
        self._session_active = False
        self._app: Optional[websocket.WebSocketApp] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_session_active(self, active: bool):
        self._session_active = active
        if self._app and self._connected:
            try:
                self._app.send(
                    json.dumps(
                        {
                            "type": "client_status",
                            "pc_id": self.pc_id,
                            "session_active": active,
                        }
                    )
                )
            except Exception:
                pass

    def run(self):
        if not HAS_WEBSOCKET:
            logger.warning("websocket-client not installed; realtime push disabled")
            return

        while self.running:
            self._connected = False
            try:
                self._app = websocket.WebSocketApp(
                    http_to_ws_url(self.server_url),
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                self._app.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                logger.debug("WebSocket loop ended: %s", exc)
            finally:
                was_connected = self._connected
                self._connected = False
                if was_connected:
                    self.server_offline.emit()

            if self.running:
                time.sleep(2)

    def _on_open(self, ws):
        self._connected = True
        ws.send(
            json.dumps(
                {
                    "type": "client_register",
                    "pc_id": self.pc_id,
                    "session_active": self._session_active,
                }
            )
        )
        self.server_online.emit()

    def _on_message(self, ws, message: str):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "commands":
            commands = data.get("commands") or []
            if commands:
                self.command_signal.emit(commands)
        elif msg_type == "config_update":
            config = data.get("config_updates")
            if config:
                self.config_update.emit(config)
        elif msg_type == "registered" and data.get("config_updates"):
            self.config_update.emit(data["config_updates"])
            commands = data.get("commands") or []
            if commands:
                self.command_signal.emit(commands)

    def _on_close(self, ws, status_code, msg):
        if self._connected:
            self._connected = False
            self.server_offline.emit()

    def _on_error(self, ws, error):
        logger.debug("WebSocket error: %s", error)

    def stop(self, wait: bool = True):
        self.running = False
        if self._app:
            try:
                self._app.close()
            except Exception:
                pass
        if wait:
            self.wait(3000)
