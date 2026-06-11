import json
import os
from datetime import datetime
from typing import Any, Dict, List


class OfflineManager:
    """Manages offline queue for actions that need to be synced later."""
    
    def __init__(self):
        self.queue_file = "offline_queue.json"
        self.queue = self._load_queue()
    
    def _load_queue(self) -> List[Dict[str, Any]]:
        """Load queue from file."""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_queue(self):
        """Save queue to file."""
        with open(self.queue_file, "w") as f:
            json.dump(self.queue, f)
    
    def queue_action(self, action_type: str, payload: Dict[str, Any]):
        """Add an action to the offline queue."""
        action = {
            "id": len(self.queue) + 1,
            "type": action_type,
            "payload": payload,
            "created_at": datetime.now().isoformat(),
            "synced": False,
        }
        self.queue.append(action)
        self._save_queue()
    
    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get all pending (unsynced) actions."""
        return [a for a in self.queue if not a["synced"]]
    
    def mark_synced(self, action_id: int):
        """Mark an action as synced."""
        for action in self.queue:
            if action["id"] == action_id:
                action["synced"] = True
                break
        self._save_queue()
    
    def clear_synced(self):
        """Remove all synced actions from queue."""
        self.queue = [a for a in self.queue if not a["synced"]]
        self._save_queue()
    
    def sync_queue(self, server_url: str) -> bool:
        """Try to sync all pending actions to server."""
        import requests
        
        pending = self.get_pending_actions()
        if not pending:
            return True
        
        try:
            for action in pending:
                response = requests.post(
                    f"{server_url}/api/sync/push",
                    json=action,
                    timeout=10,
                )
                if response.status_code == 200:
                    self.mark_synced(action["id"])
            
            self.clear_synced()
            return True
        
        except requests.exceptions.RequestException:
            return False
