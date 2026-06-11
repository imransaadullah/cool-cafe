import requests
from PyQt6.QtCore import QThread, pyqtSignal
import time
from services.config_manager import client_config


class HeartbeatThread(QThread):
    """Thread that sends heartbeat to server and monitors session status."""
    
    lock_signal = pyqtSignal()  # Signal to lock the screen
    status_update = pyqtSignal(dict)  # Signal with status update
    
    def __init__(self, pc_id: int, server_url: str = None):
        super().__init__()
        self.pc_id = pc_id
        self.server_url = server_url or client_config.get_server_url()
        self.running = True
        self.heartbeat_interval = client_config.get_heartbeat_interval()
    
    def run(self):
        while self.running:
            try:
                response = requests.get(
                    f"{self.server_url}/api/sessions/heartbeat/{self.pc_id}",
                    timeout=5,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.status_update.emit(data)
                    
                    # Check if should lock
                    if data.get("status") == "locked":
                        self.lock_signal.emit()
                        break
                else:
                    # Server error - check local cache
                    self._check_local_cache()
            
            except requests.exceptions.RequestException:
                # Connection error - check local cache
                self._check_local_cache()
            
            time.sleep(self.heartbeat_interval)
    
    def _check_local_cache(self):
        """Check local cache when server is unreachable."""
        import json
        import os
        from datetime import datetime
        
        cache_file = "session_cache.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    end_time_str = data.get("end_time")
                    if end_time_str:
                        end_time = datetime.fromisoformat(end_time_str)
                        if end_time <= datetime.now():
                            # Session expired
                            self.lock_signal.emit()
            except Exception:
                pass
    
    def stop(self):
        """Stop the heartbeat thread."""
        self.running = False
        self.wait()
