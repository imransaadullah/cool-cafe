"""
Enhanced Heartbeat Service
Sends heartbeat to server and receives security updates
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
from services.session import _parse_datetime, _utc_now


class HeartbeatThread(QThread):
    """Thread that sends heartbeat to server and monitors session status."""
    
    lock_signal = pyqtSignal()  # Signal to lock the screen
    status_update = pyqtSignal(dict)  # Signal with status update
    ban_signal = pyqtSignal()  # Signal if PC is banned
    alarm_signal = pyqtSignal(dict)  # Signal if alarm is triggered
    config_update = pyqtSignal(dict)  # Signal for config updates from server
    
    def __init__(self, pc_id: int, server_url: str = None):
        super().__init__()
        self.pc_id = pc_id
        self.server_url = server_url or client_config.get_server_url()
        self.running = True
        self.heartbeat_interval = client_config.get_heartbeat_interval()
        self.session_active = False
        self.app_version = "1.0.0"
    
    def set_session_active(self, active: bool):
        """Update session status."""
        self.session_active = active
    
    def run(self):
        while self.running:
            try:
                # Send heartbeat with security data
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
                    
                    # Check if PC is banned
                    if data.get("is_banned"):
                        self.ban_signal.emit()
                    
                    # Check if alarm is active
                    if data.get("alarm_active"):
                        self.alarm_signal.emit({"reason": "server_reported"})
                    
                    # Handle config updates
                    if data.get("config_updates"):
                        self.config_update.emit(data["config_updates"])
                        
                else:
                    # Server error - check local cache
                    self._check_local_cache()
            
            except requests.exceptions.RequestException:
                # Connection error - check local cache
                self._check_local_cache()
            
            time.sleep(self.heartbeat_interval)
    
    def _check_local_cache(self):
        """Check local cache when server is unreachable."""
        cache_file = app_path("session_cache.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    end_time_str = data.get("end_time")
                    if end_time_str:
                        end_time = _parse_datetime(end_time_str)
                        if end_time <= _utc_now():
                            # Session expired
                            self.lock_signal.emit()
            except Exception:
                pass
    
    def report_bypass(self, event_type: str):
        """Report bypass attempt to server."""
        try:
            requests.post(
                f"{self.server_url}/api/pcs/{self.pc_id}/report-bypass",
                params={"event_type": event_type},
                timeout=5,
            )
        except requests.exceptions.RequestException:
            # Queue for offline sync
            self._queue_offline_event("bypass_attempt", {"event_type": event_type})
    
    def report_alarm(self):
        """Report alarm trigger to server."""
        try:
            requests.post(
                f"{self.server_url}/api/pcs/{self.pc_id}/report-alarm",
                timeout=5,
            )
        except requests.exceptions.RequestException:
            self._queue_offline_event("alarm_triggered", {})
    
    def _queue_offline_event(self, event_type: str, details: dict):
        """Queue event for offline sync."""
        import json
        import os
        from datetime import datetime
        
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
    
    def stop(self):
        """Stop the heartbeat thread."""
        self.running = False
        self.wait()
