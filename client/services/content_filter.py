"""
Content Filter Client Service
Fetches and applies filtering rules from the server
"""

import requests
import json
import os
import platform
import subprocess
import logging
from typing import List, Dict, Any

from services.config_manager import client_config

logger = logging.getLogger(__name__)


class ContentFilterClient:
    """Client-side content filtering service."""

    def __init__(self, server_url: str, pc_id: int, branch_id: int | None = None):
        self.server_url = server_url
        self.pc_id = pc_id
        self.branch_id = branch_id
        self.platform = platform.system().lower()
        self.hosts_file = self._get_hosts_file_path()
        self.filter_config_file = "filter_config.json"
    
    def _get_hosts_file_path(self) -> str:
        """Get the hosts file path based on platform."""
        if self.platform == "windows":
            return r"C:\Windows\System32\drivers\etc\hosts"
        else:
            return "/etc/hosts"
    
    def fetch_rules(self) -> Dict[str, Any]:
        """Fetch filter rules from server."""
        try:
            params = {}
            if self.branch_id is not None:
                params["branch_id"] = self.branch_id
            response = requests.get(
                f"{self.server_url}/api/content-filter/rules",
                params=params,
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch filter rules: {e}")

        return self._load_cached_rules()
    
    def _load_cached_rules(self) -> Dict[str, Any]:
        """Load cached filter rules."""
        if os.path.exists(self.filter_config_file):
            try:
                with open(self.filter_config_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"dns": [], "process": [], "url": []}
    
    def _save_cached_rules(self, rules: Dict[str, Any]):
        """Cache filter rules locally."""
        try:
            with open(self.filter_config_file, "w") as f:
                json.dump(rules, f)
        except Exception as e:
            logger.error(f"Failed to cache filter rules: {e}")
    
    def apply_rules(self, rules: Dict[str, Any]):
        """Apply filter rules locally."""
        if client_config.is_filtering_enabled("dns_blocking"):
            self._apply_dns_rules(rules.get("dns", []))
        if client_config.is_filtering_enabled("process_blocking"):
            self._apply_process_rules(rules.get("process", []))
        self._save_cached_rules(rules)
    
    def _apply_dns_rules(self, rules: List[Dict[str, Any]]):
        """Apply DNS blocking rules to hosts file."""
        try:
            # Read current hosts file
            with open(self.hosts_file, "r") as f:
                content = f.read()
            
            # Remove old CyberCafe entries
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if "# CyberCafe Block" not in line:
                    new_lines.append(line)
            
            # Add blocked domains
            for rule in rules:
                if rule.get("action") == "block":
                    domain = rule.get("pattern")
                    if domain:
                        new_lines.append(f"127.0.0.1 {domain} # CyberCafe Block")
            
            # Write updated hosts file
            with open(self.hosts_file, "w") as f:
                f.write("\n".join(new_lines))
            
            # Flush DNS cache
            self._flush_dns_cache()
            
            logger.info(f"Applied {len(rules)} DNS rules")
            
        except PermissionError:
            logger.warning("Cannot modify hosts file. Run as administrator.")
        except Exception as e:
            logger.error(f"Error applying DNS rules: {e}")
    
    def _apply_process_rules(self, rules: List[Dict[str, Any]]):
        """Apply process blocking rules."""
        blocked_processes = [
            rule.get("pattern")
            for rule in rules
            if rule.get("action") == "block" and rule.get("pattern")
        ]
        
        if blocked_processes:
            # Store for watchdog to check
            self._save_process_blocklist(blocked_processes)
            # Kill any running blocked processes
            self._kill_blocked_processes(blocked_processes)
    
    def _save_process_blocklist(self, processes: List[str]):
        """Save blocked process list."""
        try:
            with open("blocked_processes.json", "w") as f:
                json.dump(processes, f)
        except Exception as e:
            logger.error(f"Error saving process blocklist: {e}")
    
    def _kill_blocked_processes(self, processes: List[str]):
        """Kill any running blocked processes."""
        for process in processes:
            try:
                if self.platform == "windows":
                    subprocess.run(
                        ["taskkill", "/F", "/IM", process],
                        capture_output=True,
                    )
                else:
                    subprocess.run(
                        ["pkill", "-f", process],
                        capture_output=True,
                    )
            except Exception:
                pass
    
    def _flush_dns_cache(self):
        """Flush DNS cache after updating hosts file."""
        try:
            if self.platform == "windows":
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
            elif self.platform == "darwin":
                subprocess.run(["sudo", "dscacheutil", "-flushcache"], capture_output=True)
            else:
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], capture_output=True)
        except Exception:
            pass
    
    def check_url(self, url: str) -> bool:
        """Check if a URL is blocked."""
        rules = self._load_cached_rules()
        
        for rule in rules.get("url", []):
            if rule.get("action") == "block":
                pattern = rule.get("pattern", "").lower()
                if pattern in url.lower():
                    return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get filter status."""
        rules = self._load_cached_rules()
        return {
            "dns_rules": len(rules.get("dns", [])),
            "process_rules": len(rules.get("process", [])),
            "url_rules": len(rules.get("url", [])),
        }
    
    def sync_with_server(self):
        """Sync filter rules with server."""
        rules = self.fetch_rules()
        self.apply_rules(rules)
        logger.info("Synced filter rules with server")


# Global instance
content_filter_client = None


def init_content_filter(server_url: str, pc_id: int):
    """Initialize the content filter client."""
    global content_filter_client
    content_filter_client = ContentFilterClient(server_url, pc_id)
    return content_filter_client


def get_content_filter() -> ContentFilterClient:
    """Get the content filter client instance."""
    return content_filter_client
