"""
Master Code Validation Service
Handles validation of master codes (online and offline)
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Tuple, Optional
from shared.code_utils import normalize_master_code
from services.config_manager import client_config


class MasterCodeValidator:
    """Validates master codes online and offline."""
    
    def __init__(self):
        self.server_url = client_config.get_server_url()
        self.pc_id = client_config.get_pc_id()
        self.local_cache_file = "master_code_cache.json"
        self._load_local_cache()
    
    def _load_local_cache(self):
        """Load cached master code validation."""
        if os.path.exists(self.local_cache_file):
            try:
                with open(self.local_cache_file, "r") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache = {}
    
    def _save_local_cache(self):
        """Save master code validation to local file."""
        with open(self.local_cache_file, "w") as f:
            json.dump(self.cache, f)
    
    def validate(self, code: str) -> Tuple[bool, str, Optional[float]]:
        """
        Validate a master code.
        
        Returns:
            (success, message, duration_minutes)
        """
        code = normalize_master_code(code.strip())
        if not code:
            return False, "Please enter a code", None

        # Try online validation first
        success, message, duration = self._validate_online(code)
        
        if success:
            return True, message, duration
        
        # If server unreachable, try offline validation
        if "Connection" in message or "timeout" in message.lower():
            return self._validate_offline(code)
        
        # Server responded with error
        return False, message, None
    
    def _validate_online(self, code: str) -> Tuple[bool, str, Optional[float]]:
        """Validate code with server."""
        try:
            response = requests.post(
                f"{self.server_url}/api/master-codes/validate",
                json={"code": code, "pc_id": self.pc_id},
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Cache the validation for offline use
                    self.cache[code] = {
                        "valid": True,
                        "duration": data.get("duration_minutes"),
                        "timestamp": datetime.now().isoformat(),
                    }
                    self._save_local_cache()
                    
                    return True, data.get("message"), data.get("duration_minutes")
                else:
                    return False, data.get("message"), None
            else:
                return False, f"Server error: {response.status_code}", None
                
        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {str(e)}", None
    
    def _validate_offline(self, code: str) -> Tuple[bool, str, Optional[float]]:
        """Validate code offline (static code only)."""
        # Check if this is the static master code
        static_code = client_config.get("security.static_master_code")
        
        if not static_code:
            return False, "No static code configured", None
        
        if code != normalize_master_code(static_code):
            return False, "Invalid code", None
        
        # Check if static code was already used
        static_used_at = client_config.get("security.static_code_used_at")
        if static_used_at:
            # Check if usage was reported to server
            # If so, the static code is expired
            return False, "Static code expired (already used)", None
        
        # Mark static code as used locally
        client_config.set("security.static_code_used_at", datetime.now().isoformat())
        
        # Queue for sync when online
        self._queue_offline_event("static_code_used", {
            "code": code[:4] + "****",
            "timestamp": datetime.now().isoformat(),
        })
        
        return True, "Static code accepted (offline mode)", 60  # Default 60 min
    
    def _queue_offline_event(self, event_type: str, details: dict):
        """Queue event for offline sync."""
        queue_file = "offline_queue.json"
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
    
    def invalidate_static_code(self):
        """Invalidate the static code (called after reconnection)."""
        static_used_at = client_config.get("security.static_code_used_at")
        if static_used_at:
            # Report to server that static code was used
            try:
                requests.post(
                    f"{self.server_url}/api/pcs/{self.pc_id}/report-static-code-used",
                    timeout=10,
                )
                # Clear local usage marker
                client_config.set("security.static_code_used_at", None)
            except requests.exceptions.RequestException:
                # Will be synced later
                pass
    
    def get_recovery_combo(self) -> list:
        """Get the recovery key combination."""
        from services.recovery_combo import parse_recovery_combo

        combo_str = client_config.get("security.recovery_combo", "")
        if combo_str:
            return parse_recovery_combo(combo_str)
        return []
    
    def is_banned(self) -> bool:
        """Check if PC is banned (requires online check)."""
        try:
            response = requests.get(
                f"{self.server_url}/api/pcs/{self.pc_id}/config",
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("is_banned", False)
        except requests.exceptions.RequestException:
            pass
        
        return False
