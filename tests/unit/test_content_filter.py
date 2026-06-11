"""
Unit tests for content filter service
"""

import pytest
from local_server.app.services.content_filter import (
    DNSFilter,
    ProcessFilter,
    URLFilter,
    ContentFilterManager,
)


class TestDNSFilter:
    """Test DNS filter functionality."""
    
    def setup_method(self):
        self.dns_filter = DNSFilter()
    
    def test_block_domain(self):
        """Test blocking a domain."""
        self.dns_filter.block_domain("facebook.com")
        assert self.dns_filter.is_domain_blocked("facebook.com")
    
    def test_unblock_domain(self):
        """Test unblocking a domain."""
        self.dns_filter.block_domain("facebook.com")
        self.dns_filter.unblock_domain("facebook.com")
        assert not self.dns_filter.is_domain_blocked("facebook.com")
    
    def test_multiple_domains(self):
        """Test blocking multiple domains."""
        domains = ["facebook.com", "twitter.com", "instagram.com"]
        for domain in domains:
            self.dns_filter.block_domain(domain)
        
        for domain in domains:
            assert self.dns_filter.is_domain_blocked(domain)


class TestProcessFilter:
    """Test process filter functionality."""
    
    def setup_method(self):
        self.process_filter = ProcessFilter()
    
    def test_block_process(self):
        """Test blocking a process."""
        self.process_filter.block_process("game.exe")
        assert self.process_filter.is_process_blocked("game.exe")
        assert self.process_filter.is_process_blocked("GAME.EXE")
    
    def test_unblock_process(self):
        """Test unblocking a process."""
        self.process_filter.block_process("game.exe")
        self.process_filter.unblock_process("game.exe")
        assert not self.process_filter.is_process_blocked("game.exe")
    
    def test_get_blocked_processes(self):
        """Test getting list of blocked processes."""
        processes = ["game.exe", "chat.exe"]
        for process in processes:
            self.process_filter.block_process(process)
        
        blocked = self.process_filter.get_blocked_processes()
        assert len(blocked) == 2
        assert "game.exe" in blocked
        assert "chat.exe" in blocked


class TestURLFilter:
    """Test URL filter functionality."""
    
    def setup_method(self):
        self.url_filter = URLFilter()
    
    def test_block_url(self):
        """Test blocking a URL."""
        self.url_filter.block_url("https://facebook.com")
        assert self.url_filter.is_url_blocked("https://facebook.com")
    
    def test_block_keyword(self):
        """Test blocking a keyword."""
        self.url_filter.block_keyword("gambling")
        assert self.url_filter.is_url_blocked("https://www.gambling-site.com")
    
    def test_check_url(self):
        """Test URL check with details."""
        self.url_filter.block_keyword("adult")
        result = self.url_filter.check_url("https://www.adult-site.com")
        assert result["is_blocked"] is True
        assert len(result["matched_rules"]) > 0
    
    def test_allowed_url(self):
        """Test that non-blocked URLs are allowed."""
        result = self.url_filter.check_url("https://www.google.com")
        assert result["is_blocked"] is False


class TestContentFilterManager:
    """Test content filter manager."""
    
    def setup_method(self):
        self.manager = ContentFilterManager()
    
    def test_load_rules(self):
        """Test loading rules."""
        rules = [
            {"rule_type": "dns", "pattern": "facebook.com", "action": "block"},
            {"rule_type": "process", "pattern": "game.exe", "action": "block"},
            {"rule_type": "url", "pattern": "gambling", "action": "block"},
        ]
        self.manager.load_rules(rules)
        assert len(self.manager.dns_filter.rules) == 1
        assert len(self.manager.process_filter.rules) == 1
        assert len(self.manager.url_filter.rules) == 1
    
    def test_get_status(self):
        """Test getting filter status."""
        status = self.manager.get_status()
        assert "dns_rules" in status
        assert "process_rules" in status
        assert "url_rules" in status
