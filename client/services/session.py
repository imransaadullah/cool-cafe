import requests
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union
from services.config_manager import client_config
from services.paths import app_path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Union[str, datetime]) -> datetime:
    """Parse server/cache datetimes and normalize to UTC."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SessionManager:
    def __init__(self):
        self.server_url = client_config.get_server_url()
        self.session_id = None
        self.end_time = None
        self.is_active = False
        self.remaining_seconds = 0
        self.local_cache_file = app_path("session_cache.json")
        self._load_local_cache()
    
    def _load_local_cache(self):
        """Load cached session from local file."""
        if os.path.exists(self.local_cache_file):
            try:
                with open(self.local_cache_file, "r") as f:
                    data = json.load(f)
                    self.session_id = data.get("session_id")
                    end_time_str = data.get("end_time")
                    if end_time_str:
                        self.end_time = _parse_datetime(end_time_str)
                        if self.end_time > _utc_now():
                            self.is_active = True
                            self.remaining_seconds = (
                                self.end_time - _utc_now()
                            ).total_seconds()
                        else:
                            self._clear_local_cache()
            except Exception:
                self._clear_local_cache()
    
    def _save_local_cache(self):
        """Save session to local file for offline resilience."""
        data = {
            "session_id": self.session_id,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
        with open(self.local_cache_file, "w") as f:
            json.dump(data, f)
    
    def _clear_local_cache(self):
        """Clear local session cache."""
        self.session_id = None
        self.end_time = None
        self.is_active = False
        self.remaining_seconds = 0
        if os.path.exists(self.local_cache_file):
            os.remove(self.local_cache_file)
    
    def redeem_code(
        self, code: str, pc_id: int
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        Try to redeem a code with the server.
        Returns: (success, message, session_data)
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/redeem-code",
                json={"code": code, "pc_id": pc_id},
                timeout=10,
            )
            data = response.json()
            
            if response.status_code == 200 and data.get("success"):
                return True, data.get("message"), data
            return False, data.get("message", "Failed to redeem code"), data
        
        except requests.exceptions.RequestException:
            # Offline mode - try to use cached code validation
            return self._offline_code_validation(code, pc_id)
    
    def _offline_code_validation(
        self, code: str, pc_id: int
    ) -> Tuple[bool, str, Optional[dict]]:
        """Validate code when server is offline (basic validation)."""
        # In offline mode, we can only validate if we have cached codes
        # For now, return failure
        return False, "Server offline. Please try again later.", None
    
    def start_session(self, session_data: dict):
        """Start a session with the given data."""
        self.session_id = session_data.get("session_id")
        end_time_str = session_data.get("end_time")
        
        if end_time_str:
            self.end_time = _parse_datetime(end_time_str)
        else:
            duration = session_data.get("duration_minutes", 60)
            self.end_time = _utc_now() + timedelta(minutes=duration)

        self.is_active = True
        self.remaining_seconds = (self.end_time - _utc_now()).total_seconds()
        self._save_local_cache()
    
    def pause_session(self) -> Tuple[bool, str]:
        """Pause the current session on the server and clear local active state."""
        if not self.is_active:
            return False, "No active session"

        session_id = self.session_id
        message = "Could not pause session"
        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/pause",
                params={"session_id": session_id},
                timeout=10,
            )
            if response.status_code == 200:
                message = "Session paused"
            else:
                detail = response.json().get("detail", message)
                message = detail if isinstance(detail, str) else message
                return False, message
        except requests.exceptions.RequestException:
            return False, "Server offline. Please try again later."

        self.is_active = False
        self.remaining_seconds = 0
        self.end_time = None
        if os.path.exists(self.local_cache_file):
            os.remove(self.local_cache_file)
        return True, message

    def get_resume_info(self, pc_id: int) -> Optional[dict]:
        """Fetch paused session resume eligibility from the server."""
        try:
            response = requests.get(
                f"{self.server_url}/api/sessions/pc/{pc_id}/resume-info",
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return None

    def resume_paused_session(
        self, session_id: int
    ) -> Tuple[bool, str, Optional[dict]]:
        """Resume a paused session without redeeming a new code."""
        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/resume",
                params={"session_id": session_id},
                timeout=10,
            )
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                return True, data.get("message", "Session resumed"), data
            return False, data.get("message", "Cannot resume session"), None
        except requests.exceptions.RequestException:
            return False, "Server offline. Please try again later.", None
    
    def resume_session(self):
        """Resume a paused session (legacy helper)."""
        if self.session_id is None:
            return False
        success, _message, data = self.resume_paused_session(self.session_id)
        if success and data:
            self.start_session(data)
            return True
        return False
    
    def end_session(self):
        """End the current session."""
        if self.session_id:
            try:
                requests.post(
                    f"{self.server_url}/api/sessions/stop",
                    params={"session_id": self.session_id},
                    timeout=10,
                )
            except requests.exceptions.RequestException:
                pass
        
        self._clear_local_cache()
    
    def get_remaining_seconds(self) -> float:
        """Get remaining time in seconds."""
        if self.end_time:
            remaining = (self.end_time - _utc_now()).total_seconds()
            return max(0, remaining)
        return 0
