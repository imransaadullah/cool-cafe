"""Coordinates security modules for the lock screen."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from services.alarm import alarm_service
from services.config_manager import client_config
from services.content_filter import ContentFilterClient
from services.security_monitor import SecurityMonitor, UninstallDetector
from shared.app_policy import resolve_client_mode

logger = logging.getLogger(__name__)


class SecurityController(QObject):
    """Wire security monitor, content filter, and alarm into the client UI."""

    force_lock = pyqtSignal()
    force_logout = pyqtSignal()
    refresh_rules = pyqtSignal(dict)
    extend_session = pyqtSignal(float)

    def __init__(self, lock_screen):
        super().__init__()
        self.lock_screen = lock_screen
        self.monitor: Optional[SecurityMonitor] = None
        self.uninstall_detector: Optional[UninstallDetector] = None
        self.content_filter: Optional[ContentFilterClient] = None
        self.app_policy: Dict[str, Any] = {}
        self.server_config: Dict[str, Any] = {}

        pc_id = client_config.get_pc_id()
        server_url = client_config.get_server_url()
        branch_id = client_config.get_branch_id()
        self.content_filter = ContentFilterClient(server_url, pc_id, branch_id)

    def start(self):
        if client_config.is_production_mode():
            self._start_uninstall_detector()

    def stop(self):
        if self.monitor:
            self.monitor.stop()
            self.monitor = None
        if self.uninstall_detector:
            self.uninstall_detector.stop()
            self.uninstall_detector = None

    def on_session_started(self):
        if not self.monitor:
            self.monitor = SecurityMonitor(client_config.get_pc_id())
            self.monitor.bypass_detected.connect(self._on_bypass)
            self.monitor.alarm_trigger.connect(self._on_alarm)
            self.monitor.start()
        self.monitor.set_app_policy(self.app_policy)
        self.monitor.set_enforcement_enabled(True)
        self._apply_filtering()

    def on_session_ended(self):
        if self.monitor:
            self.monitor.set_enforcement_enabled(False)

    def apply_server_config(self, config: Dict[str, Any]):
        self.server_config = config or {}
        if config.get("app_policy"):
            self.app_policy = config["app_policy"]
            if self.monitor:
                self.monitor.set_app_policy(self.app_policy)

        security = config.get("security") or {}
        if security.get("recovery_combo"):
            client_config.set("security.recovery_combo", security["recovery_combo"])
        if security.get("alarm_color"):
            client_config.set("security.alarm_color", security["alarm_color"])

        mode = resolve_client_mode(config, client_config.get("mode"))
        client_config.set_mode(mode)

    def handle_commands(self, commands: list):
        for command in commands or []:
            cmd_type = command.get("type")
            payload = command.get("payload") or {}
            if cmd_type == "force_lock":
                self.force_lock.emit()
            elif cmd_type == "force_logout":
                self.force_logout.emit()
            elif cmd_type == "refresh_rules":
                self.refresh_rules.emit(self.server_config)
            elif cmd_type == "extend":
                minutes = float(payload.get("additional_minutes", 0))
                if minutes > 0:
                    self.extend_session.emit(minutes)

    def _apply_filtering(self):
        if not self.content_filter:
            return
        filtering = self.server_config.get("filtering") or {}
        if filtering:
            self.content_filter.apply_rules(filtering)
        else:
            self.content_filter.sync_with_server()

    def refresh_filter_rules(self, config: Optional[Dict[str, Any]] = None):
        if config:
            self.apply_server_config(config)
        self._apply_filtering()

    def _on_bypass(self, event_type: str, detail: str):
        logger.warning("Security bypass: %s — %s", event_type, detail)
        heartbeat = getattr(self.lock_screen, "heartbeat_thread", None)
        if heartbeat:
            heartbeat.report_bypass(event_type)
        if client_config.get("security.alarm_enabled", True):
            if alarm_service.increment_wrong_attempts():
                self._trigger_alarm(detail)

    def _on_alarm(self, reason: str):
        self._trigger_alarm(reason)

    def _trigger_alarm(self, reason: str):
        heartbeat = getattr(self.lock_screen, "heartbeat_thread", None)
        if heartbeat:
            heartbeat.report_alarm()
        alarm_service.trigger_alarm(reason)

    def _start_uninstall_detector(self):
        if self.uninstall_detector:
            return
        self.uninstall_detector = UninstallDetector()
        self.uninstall_detector.uninstall_detected.connect(
            lambda: self._trigger_alarm("Uninstall attempt detected")
        )
        self.uninstall_detector.start()
