"""
Security Monitor Service
Detects bypass attempts and enforces merged app policy during sessions.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from services.config_manager import client_config
from shared.app_policy import is_process_allowed

logger = logging.getLogger(__name__)


class SecurityMonitor(QThread):
    """Thread that monitors for security breaches and enforces app policy."""

    bypass_detected = pyqtSignal(str, str)
    alarm_trigger = pyqtSignal(str)

    def __init__(self, pc_id: int):
        super().__init__()
        self.pc_id = pc_id
        self.running = True
        self.enforcement_enabled = False
        self.check_interval = 3
        self.app_policy: Dict[str, Any] = {}

    def set_app_policy(self, policy: Optional[Dict[str, Any]]):
        self.app_policy = policy or {}

    def set_enforcement_enabled(self, enabled: bool):
        self.enforcement_enabled = enabled

    def run(self):
        while self.running:
            try:
                if self.enforcement_enabled and self.app_policy:
                    self._enforce_process_policy()
                if client_config.is_production_mode():
                    self._check_service_status()
            except Exception as exc:
                logger.warning("Security monitor error: %s", exc)

            time.sleep(self.check_interval)

    def _enforce_process_policy(self):
        if not client_config.is_filtering_enabled("process_blocking"):
            return

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info["name"]
                if not proc_name:
                    continue
                if is_process_allowed(proc_name, self.app_policy):
                    continue
                self.bypass_detected.emit(
                    "blocked_process",
                    f"Blocked: {proc_name}",
                )
                self._kill_process(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def _check_service_status(self):
        if not client_config.get("security.run_as_service", False):
            return

        if sys.platform != "win32":
            return

        try:
            result = subprocess.run(
                ["sc", "query", "CyberCafeWatchdog"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "RUNNING" not in result.stdout:
                self.bypass_detected.emit(
                    "service_stopped",
                    "Watchdog service not running",
                )
        except Exception:
            pass

    def _kill_process(self, pid: int):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                os.kill(pid, 9)
        except Exception:
            pass

    def stop(self):
        self.running = False
        self.wait(5000)


class UninstallDetector(QThread):
    """Detects if someone is trying to uninstall the client."""

    uninstall_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.running = True
        self.check_interval = 2

    def run(self):
        while self.running:
            try:
                self._check_uninstaller_running()
            except Exception:
                pass
            time.sleep(self.check_interval)

    def _check_uninstaller_running(self):
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                proc_name = (proc.info["name"] or "").lower()
                if "uninstall" in proc_name or proc_name == "msiexec.exe":
                    cmdline = " ".join(proc.cmdline() or []).lower()
                    if "cybercafe" in cmdline or "/x" in cmdline:
                        self.uninstall_detected.emit()
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def stop(self):
        self.running = False
        self.wait(3000)
