"""
Client Configuration Manager
Handles loading and saving client configuration
"""

import copy
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging
from services.paths import app_path

logger = logging.getLogger(__name__)


class ClientConfig:
    """Manages client configuration."""
    
    DEFAULT_CONFIG = {
        "configured": False,
        "mode": "production",
        "server_url": "http://localhost:8000",
        "pc_id": 1,
        "pc_number": 1,
        "branch_id": 1,
        "heartbeat_interval": 5,
        "offline_mode": False,
        "filtering": {
            "dns_blocking": True,
            "process_blocking": True,
            "url_filtering": True,
        },
        "security": {
            "static_master_code": "",
            "recovery_combo": "F9+F10+F11",
            "alarm_color": "#FF0000",
            "run_as_service": False,
        },
        "ui": {
            "fullscreen": True,
            "always_on_top": True,
            "theme": "dark",
        },
        "logging": {
            "level": "INFO",
            "file": "client.log",
        },
    }
    
    def __init__(self, config_path: str = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to configuration file
        """
        if config_path is None:
            config_path = app_path("config.json")

        self.config_path = Path(config_path)
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self._staff_maintenance_unlock = False
        self._load()
    
    def _load(self):
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    self._merge_config(saved_config)
                logger.info(f"Configuration loaded from {self.config_path}")
            else:
                logger.info("No configuration file found, using defaults")
                self._save()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._save()
    
    def _merge_config(self, saved_config: Dict[str, Any]):
        """Merge saved config with defaults."""
        for key, value in saved_config.items():
            if key in self.config and isinstance(value, dict) and isinstance(self.config[key], dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def _save(self):
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key doesn't exist
        
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self._save()
    
    def get_server_url(self) -> str:
        """Get the server URL."""
        return self.get("server_url", "http://localhost:8000")
    
    def get_pc_id(self) -> int:
        """Get the PC ID."""
        return self.get("pc_id", 1)
    
    def get_branch_id(self) -> int:
        """Get the branch ID."""
        return self.get("branch_id", 1)
    
    def get_heartbeat_interval(self) -> int:
        """Get the heartbeat interval in seconds."""
        interval = self.get("heartbeat_interval")
        if interval is None:
            interval = self.get("security.heartbeat_interval", 5)
        return interval or 5

    def is_configured(self) -> bool:
        """Check if the client has completed setup."""
        return bool(self.get("configured", False))
    
    def is_offline_mode(self) -> bool:
        """Check if offline mode is enabled."""
        return self.get("offline_mode", False)
    
    def is_filtering_enabled(self, filter_type: str) -> bool:
        """Check if a specific filter type is enabled."""
        return self.get(f"filtering.{filter_type}", False)

    def is_production_mode(self) -> bool:
        """True when client runs in production (kiosk-hardened) mode."""
        return self.get("mode", "production") == "production"

    def is_exit_allowed(self) -> bool:
        """Customers cannot exit in production; staff unlock enables maintenance."""
        if self._staff_maintenance_unlock:
            return True
        return not self.is_production_mode()

    def unlock_staff_maintenance(self):
        """Temporary in-memory unlock for staff (not persisted)."""
        self._staff_maintenance_unlock = True

    def lock_staff_maintenance(self):
        self._staff_maintenance_unlock = False

    def set_mode(self, mode: str):
        if mode in ("production", "dev"):
            self.set("mode", mode)
    
    def update_server_url(self, url: str):
        """Update the server URL."""
        self.set("server_url", url)
    
    def update_pc_id(self, pc_id: int):
        """Update the PC ID."""
        self.set("pc_id", pc_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get the entire configuration as a dictionary."""
        return self.config.copy()
    
    def reset(self):
        """Reset configuration to defaults."""
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self._save()
        logger.info("Configuration reset to defaults")


# Global config instance
client_config = ClientConfig()
