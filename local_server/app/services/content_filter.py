"""
Content Filtering Service
Supports DNS blocking, process blocking, and URL filtering
"""

import os
import platform
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
import json


class FilterRule:
    """Represents a single filter rule."""
    
    def __init__(self, rule_type: str, pattern: str, action: str = "block", priority: int = 0):
        self.rule_type = rule_type
        self.pattern = pattern
        self.action = action
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_type": self.rule_type,
            "pattern": self.pattern,
            "action": self.action,
            "priority": self.priority,
        }


class ContentFilter:
    """Main content filtering service."""
    
    def __init__(self):
        self.rules: List[FilterRule] = []
        self.platform = platform.system().lower()
        self.hosts_file = self._get_hosts_file_path()
    
    def _get_hosts_file_path(self) -> str:
        """Get the hosts file path based on platform."""
        if self.platform == "windows":
            return r"C:\Windows\System32\drivers\etc\hosts"
        else:
            return "/etc/hosts"
    
    def load_rules(self, rules: List[Dict[str, Any]]):
        """Load filter rules from database or config."""
        self.rules = []
        for rule_data in rules:
            rule = FilterRule(
                rule_type=rule_data.get("rule_type"),
                pattern=rule_data.get("pattern"),
                action=rule_data.get("action", "block"),
                priority=rule_data.get("priority", 0),
            )
            self.rules.append(rule)
        
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def add_rule(self, rule_type: str, pattern: str, action: str = "block", priority: int = 0):
        """Add a new filter rule."""
        rule = FilterRule(rule_type, pattern, action, priority)
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_type: str, pattern: str):
        """Remove a filter rule."""
        self.rules = [
            r for r in self.rules
            if not (r.rule_type == rule_type and r.pattern == pattern)
        ]
    
    def get_rules_by_type(self, rule_type: str) -> List[FilterRule]:
        """Get all rules of a specific type."""
        return [r for r in self.rules if r.rule_type == rule_type]


class DNSFilter(ContentFilter):
    """DNS-based content filtering."""
    
    def __init__(self):
        super().__init__()
        self.blocked_domains = set()
        self.allowed_domains = set()
    
    def apply_rules(self):
        """Apply DNS filter rules to hosts file."""
        dns_rules = self.get_rules_by_type("dns")
        
        for rule in dns_rules:
            if rule.action == "block":
                self.blocked_domains.add(rule.pattern)
            elif rule.action == "allow":
                self.allowed_domains.add(rule.pattern)
        
        self._update_hosts_file()
    
    def _update_hosts_file(self):
        """Update the hosts file with blocked domains."""
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
            
            # Add new blocked domains
            for domain in self.blocked_domains:
                if domain not in self.allowed_domains:
                    new_lines.append(f"127.0.0.1 {domain} # CyberCafe Block")
            
            # Write updated hosts file
            with open(self.hosts_file, "w") as f:
                f.write("\n".join(new_lines))
            
            # Flush DNS cache
            self._flush_dns_cache()
            
        except PermissionError:
            print("Warning: Cannot modify hosts file. Run as administrator.")
        except Exception as e:
            print(f"Error updating hosts file: {e}")
    
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
    
    def block_domain(self, domain: str):
        """Block a specific domain."""
        self.blocked_domains.add(domain)
        self._update_hosts_file()
    
    def unblock_domain(self, domain: str):
        """Unblock a specific domain."""
        self.blocked_domains.discard(domain)
        self._update_hosts_file()
    
    def is_domain_blocked(self, domain: str) -> bool:
        """Check if a domain is blocked."""
        return domain in self.blocked_domains


class ProcessFilter(ContentFilter):
    """Process-based content filtering."""
    
    def __init__(self):
        super().__init__()
        self.blocked_processes = set()
        self.allowed_processes = set()
    
    def apply_rules(self):
        """Apply process filter rules."""
        process_rules = self.get_rules_by_type("process")
        
        for rule in process_rules:
            if rule.action == "block":
                self.blocked_processes.add(rule.pattern.lower())
            elif rule.action == "allow":
                self.allowed_processes.add(rule.pattern.lower())
    
    def block_process(self, process_name: str):
        """Block a specific process."""
        self.blocked_processes.add(process_name.lower())
    
    def unblock_process(self, process_name: str):
        """Unblock a specific process."""
        self.blocked_processes.discard(process_name.lower())
    
    def is_process_blocked(self, process_name: str) -> bool:
        """Check if a process is blocked."""
        return process_name.lower() in self.blocked_processes
    
    def get_blocked_processes(self) -> List[str]:
        """Get list of blocked processes."""
        return list(self.blocked_processes)
    
    def kill_blocked_processes(self):
        """Kill any running blocked processes."""
        try:
            if self.platform == "windows":
                for process in self.blocked_processes:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", process],
                        capture_output=True,
                    )
            else:
                for process in self.blocked_processes:
                    subprocess.run(
                        ["pkill", "-f", process],
                        capture_output=True,
                    )
        except Exception as e:
            print(f"Error killing processes: {e}")


class URLFilter(ContentFilter):
    """URL-based content filtering."""
    
    def __init__(self):
        super().__init__()
        self.blocked_urls = set()
        self.allowed_urls = set()
        self.blocked_keywords = set()
    
    def apply_rules(self):
        """Apply URL filter rules."""
        url_rules = self.get_rules_by_type("url")
        
        for rule in url_rules:
            if rule.action == "block":
                if rule.pattern.startswith("http"):
                    self.blocked_urls.add(rule.pattern)
                else:
                    self.blocked_keywords.add(rule.pattern.lower())
            elif rule.action == "allow":
                if rule.pattern.startswith("http"):
                    self.allowed_urls.add(rule.pattern)
    
    def block_url(self, url: str):
        """Block a specific URL."""
        self.blocked_urls.add(url)
    
    def unblock_url(self, url: str):
        """Unblock a specific URL."""
        self.blocked_urls.discard(url)
    
    def block_keyword(self, keyword: str):
        """Block a keyword in URLs."""
        self.blocked_keywords.add(keyword.lower())
    
    def unblock_keyword(self, keyword: str):
        """Unblock a keyword in URLs."""
        self.blocked_keywords.discard(keyword.lower())
    
    def is_url_blocked(self, url: str) -> bool:
        """Check if a URL is blocked."""
        url_lower = url.lower()
        
        # Check exact URL match
        if url in self.blocked_urls:
            return True
        
        # Check keyword match
        for keyword in self.blocked_keywords:
            if keyword in url_lower:
                return True
        
        return False
    
    def check_url(self, url: str) -> Dict[str, Any]:
        """Check URL and return detailed result."""
        is_blocked = self.is_url_blocked(url)
        matched_rules = []
        
        if is_blocked:
            for keyword in self.blocked_keywords:
                if keyword in url.lower():
                    matched_rules.append(f"keyword:{keyword}")
            if url in self.blocked_urls:
                matched_rules.append(f"url:{url}")
        
        return {
            "url": url,
            "is_blocked": is_blocked,
            "matched_rules": matched_rules,
        }


class ContentFilterManager:
    """Main content filter manager."""
    
    def __init__(self):
        self.dns_filter = DNSFilter()
        self.process_filter = ProcessFilter()
        self.url_filter = URLFilter()
    
    def load_rules(self, rules: List[Dict[str, Any]]):
        """Load all filter rules."""
        self.dns_filter.load_rules(rules)
        self.process_filter.load_rules(rules)
        self.url_filter.load_rules(rules)
    
    def apply_all_rules(self):
        """Apply all filter rules."""
        self.dns_filter.apply_rules()
        self.process_filter.apply_rules()
        self.url_filter.apply_rules()
    
    def get_status(self) -> Dict[str, Any]:
        """Get filter status."""
        return {
            "dns_rules": len(self.dns_filter.rules),
            "process_rules": len(self.process_filter.rules),
            "url_rules": len(self.url_filter.rules),
            "blocked_domains": len(self.dns_filter.blocked_domains),
            "blocked_processes": len(self.process_filter.blocked_processes),
            "blocked_urls": len(self.url_filter.blocked_urls),
        }


# Global instance
content_filter = ContentFilterManager()
