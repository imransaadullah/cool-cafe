import requests
from typing import Optional, Tuple
from services.config_manager import client_config


class SessionManager:
    """Thin client — server is the single source of truth for session state."""

    def __init__(self):
        self.server_url = client_config.get_server_url()
        self.session_id: Optional[int] = None
        self.access_code: Optional[str] = None
        self.is_active = False
        self.remaining_seconds = 0.0

    def authenticate(self, code: str, pc_id: int) -> Tuple[bool, str, Optional[dict]]:
        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/authenticate",
                json={"code": code, "pc_id": pc_id},
                timeout=10,
            )
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                return True, data.get("message", "Session started"), data
            return False, data.get("message", "Authentication failed"), data
        except requests.exceptions.RequestException:
            return False, "Server offline. Please try again later.", None

    def apply_session(self, session_data: dict, code: str):
        self.session_id = session_data.get("session_id")
        self.access_code = code
        self.is_active = True
        self.remaining_seconds = float(session_data.get("remaining_seconds") or 0)

    def logout(self, pc_id: int) -> Tuple[bool, str]:
        if not self.access_code:
            return False, "No active session"

        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/logout",
                json={"code": self.access_code, "pc_id": pc_id},
                timeout=10,
            )
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                self.clear_session()
                return True, data.get("message", "Session paused")
            return False, data.get("message", "Could not logout")
        except requests.exceptions.RequestException:
            return False, "Server offline. Please try again later."

    def session_heartbeat(self, pc_id: int) -> Optional[dict]:
        if not self.access_code or not self.is_active:
            return None

        try:
            response = requests.post(
                f"{self.server_url}/api/sessions/heartbeat",
                json={"code": self.access_code, "pc_id": pc_id},
                timeout=5,
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            pass
        return None

    def clear_session(self):
        self.session_id = None
        self.access_code = None
        self.is_active = False
        self.remaining_seconds = 0.0

    def sync_from_heartbeat(self, data: dict) -> bool:
        """Update timer from server. Returns False if client should lock."""
        if data.get("should_lock"):
            return False
        self.remaining_seconds = float(data.get("remaining_seconds") or 0)
        return self.remaining_seconds > 0

    def tick(self, delta_seconds: float = 1.0):
        if self.is_active and self.remaining_seconds > 0:
            self.remaining_seconds = max(0, self.remaining_seconds - delta_seconds)

    def get_remaining_seconds(self) -> float:
        return max(0, self.remaining_seconds)
