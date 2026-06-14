"""
Enhanced Heartbeat Service
Sends PC heartbeat to server and code-based session heartbeat for authoritative timer.
"""

import requests
import platform
import json
import os
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
import time
from services.config_manager import client_config
from services.paths import app_path


OFFLINE_GRACE_INTERVALS = 6  # lock after ~6 failed session heartbeats


class HeartbeatThread(QThread):
    """Thread that sends heartbeat to server and monitors session status."""

    lock_signal = pyqtSignal()
    status_update = pyqtSignal(dict)
    session_update = pyqtSignal(dict)
    ban_signal = pyqtSignal()
    alarm_signal = pyqtSignal(dict)
    config_update = pyqtSignal(dict)
    command_signal = pyqtSignal(list)

    def __init__(self, pc_id: int, server_url: str = None, access_code: str = None):
        super().__init__()
        self.pc_id = pc_id
        self.server_url = server_url or client_config.get_server_url()
        self.access_code = access_code
        self.running = True
        self.heartbeat_interval = client_config.get_heartbeat_interval()
        self.session_active = False
        self.app_version = "1.0.0"
        self._offline_misses = 0

    def set_session_active(self, active: bool):
        self.session_active = active

    def set_access_code(self, code: str):
        self.access_code = code

    def run(self):
        while self.running:
            try:
                payload = {
                    "status": "online",
                    "session_active": self.session_active,
                    "app_version": self.app_version,
                    "platform": platform.system(),
                }

                response = requests.post(
                    f"{self.server_url}/api/pcs/{self.pc_id}/heartbeat",
                    json=payload,
                    timeout=5,
                )

                if response.status_code == 200:
                    data = response.json()
                    self.status_update.emit(data)

                    if data.get("is_banned"):
                        self.ban_signal.emit()

                    if data.get("alarm_active"):
                        self.alarm_signal.emit({"reason": "server_reported"})

                    if data.get("config_updates"):
                        self.config_update.emit(data["config_updates"])

                    if data.get("commands"):
                        self.command_signal.emit(data["commands"])

                if self.session_active and self.access_code:
                    self._send_session_heartbeat()

            except requests.exceptions.RequestException:
                if self.session_active:
                    self._offline_misses += 1
                    if self._offline_misses >= OFFLINE_GRACE_INTERVALS:
                        self.lock_signal.emit()

            time.sleep(self.heartbeat_interval)

    def _send_session_heartbeat(self):
        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/heartbeat",
                json={"code": self.access_code, "pc_id": self.pc_id},
                timeout=5,
            )
            if response.status_code == 200:
                self._offline_misses = 0
                self.session_update.emit(response.json())
            elif self.session_active:
                self._offline_misses += 1
                if self._offline_misses >= OFFLINE_GRACE_INTERVALS:
                    self.lock_signal.emit()
        except requests.exceptions.RequestException:
            if self.session_active:
                self._offline_misses += 1
                if self._offline_misses >= OFFLINE_GRACE_INTERVALS:
                    self.lock_signal.emit()

    def report_bypass(self, event_type: str):
        try:
            requests.post(
                f"{self.server_url}/api/pcs/{self.pc_id}/report-bypass",
                params={"event_type": event_type},
                timeout=5,
            )
        except requests.exceptions.RequestException:
            self._queue_offline_event("bypass_attempt", {"event_type": event_type})

    def report_alarm(self):
        try:
            requests.post(
                f"{self.server_url}/api/pcs/{self.pc_id}/report-alarm",
                timeout=5,
            )
        except requests.exceptions.RequestException:
            self._queue_offline_event("alarm_triggered", {})

    def _queue_offline_event(self, event_type: str, details: dict):
        queue_file = app_path("offline_queue.json")
        queue = []

        if os.path.exists(queue_file):
            try:
                with open(queue_file, "r") as f:
                    queue = json.load(f)
            except Exception:
                queue = []

        queue.append({
            "type": event_type,
            "pc_id": self.pc_id,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })

        with open(queue_file, "w") as f:
            json.dump(queue, f)

    def stop(self, wait: bool = True):
        self.running = False
        if wait:
            self.wait(3000)
