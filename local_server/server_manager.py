"""
CyberCafe Server Manager
Starts the API (+ embedded dashboard), opens the admin UI, and supports stop/start.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

import uvicorn
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QMenu,
)

LOCAL_SERVER = Path(__file__).resolve().parent
ROOT = LOCAL_SERVER.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LOCAL_SERVER))

from shared.config import settings
from shared.qt_single_instance import QtSingleInstanceGuard, activate_application_window
from services.install_config import apply_env_to_process, is_configured


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return get_app_dir() / "server_manager.json"


def load_manager_config() -> dict:
    defaults = {
        "auto_start": True,
        "open_browser": True,
        "host": settings.HOST,
        "port": settings.PORT,
    }
    path = config_path()
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                defaults.update(json.load(fh))
        except Exception:
            pass
    return defaults


def save_manager_config(cfg: dict) -> None:
    with open(config_path(), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server: uvicorn.Server | None = None
        self.running = False

    def run(self):
        from local_server.app.main import app

        self.running = True
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        self.running = False
        if self.server:
            self.server.should_exit = True


class ServerManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_manager_config()
        self.server_thread: ServerThread | None = None
        self._browser_opened = False

        self.setWindowTitle("CyberCafe Server")
        self.setMinimumSize(520, 360)

        self._build_menu()
        self._build_ui()
        self._setup_tray()

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._refresh_status)
        self.poll_timer.start(2000)

        if self.cfg.get("auto_start", True):
            QTimer.singleShot(500, self.start_services)

    def _build_menu(self):
        menu = self.menuBar().addMenu("Settings")
        setup_action = QAction("Run Setup Wizard…", self)
        setup_action.triggered.connect(self._open_setup_wizard)
        menu.addAction(setup_action)

    def _open_setup_wizard(self):
        if self.server_thread and self.server_thread.running:
            QMessageBox.information(
                self,
                "Stop Services First",
                "Stop the running services before changing installation settings.",
            )
            return
        from ui.setup_wizard import ServerSetupWizard

        self._setup_window = ServerSetupWizard(on_complete=self._after_setup_rerun)
        self._setup_window.show()

    def _after_setup_rerun(self):
        apply_env_to_process()
        self.cfg = load_manager_config()
        self.auto_start_cb.setChecked(self.cfg.get("auto_start", True))
        self.open_browser_cb.setChecked(self.cfg.get("open_browser", True))
        if self.cfg.get("auto_start", True):
            self.start_services()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("CyberCafe Server Manager")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self.api_status = QLabel("API: Stopped")
        self.api_status.setStyleSheet("font-size: 15px; color: #c0392b;")
        status_layout.addWidget(self.api_status)

        self.dashboard_status = QLabel("Dashboard: Stopped")
        self.dashboard_status.setStyleSheet("font-size: 15px; color: #c0392b;")
        status_layout.addWidget(self.dashboard_status)

        self.url_label = QLabel(self._dashboard_url())
        self.url_label.setStyleSheet("color: #555;")
        status_layout.addWidget(self.url_label)

        layout.addWidget(status_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_services)
        self.start_btn.setStyleSheet("background:#2e7d32;color:white;padding:10px 18px;")
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_services)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background:#c62828;color:white;padding:10px 18px;")
        btn_row.addWidget(self.stop_btn)

        self.open_btn = QPushButton("Open Dashboard")
        self.open_btn.clicked.connect(self.open_dashboard)
        self.open_btn.setStyleSheet("background:#1565c0;color:white;padding:10px 18px;")
        btn_row.addWidget(self.open_btn)

        layout.addLayout(btn_row)

        opts_group = QGroupBox("Options")
        opts_layout = QVBoxLayout(opts_group)
        self.auto_start_cb = QCheckBox("Start services when this app opens")
        self.auto_start_cb.setChecked(self.cfg.get("auto_start", True))
        self.auto_start_cb.toggled.connect(self._save_options)
        opts_layout.addWidget(self.auto_start_cb)

        self.open_browser_cb = QCheckBox("Open dashboard in browser when services start")
        self.open_browser_cb.setChecked(self.cfg.get("open_browser", True))
        self.open_browser_cb.toggled.connect(self._save_options)
        opts_layout.addWidget(self.open_browser_cb)
        layout.addWidget(opts_group)

        hint = QLabel(
            "PostgreSQL must be running and configured in .env before starting.\n"
            "Clients connect to this machine on the API port."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666;font-size:12px;")
        layout.addWidget(hint)
        layout.addStretch()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        start_action = QAction("Start Services", self)
        start_action.triggered.connect(self.start_services)
        menu.addAction(start_action)

        stop_action = QAction("Stop Services", self)
        stop_action.triggered.connect(self.stop_services)
        menu.addAction(stop_action)

        open_action = QAction("Open Dashboard", self)
        open_action.triggered.connect(self.open_dashboard)
        menu.addAction(open_action)

        menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _host(self) -> str:
        return self.cfg.get("host", settings.HOST)

    def _port(self) -> int:
        return int(self.cfg.get("port", settings.PORT))

    def _api_url(self) -> str:
        host = "127.0.0.1" if self._host() in ("0.0.0.0", "::") else self._host()
        return f"http://{host}:{self._port()}"

    def _dashboard_url(self) -> str:
        return self._api_url() + "/"

    def _health_ok(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self._api_url()}/api/health", timeout=2) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def start_services(self):
        if self.server_thread and self.server_thread.running:
            self.open_dashboard()
            return

        host = self._host()
        port = self._port()
        self.server_thread = ServerThread(host, port)
        self.server_thread.start()
        self._browser_opened = False

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.api_status.setText("API: Starting…")
        self.api_status.setStyleSheet("font-size: 15px; color: #e67e22;")
        self.dashboard_status.setText("Dashboard: Starting…")
        self.dashboard_status.setStyleSheet("font-size: 15px; color: #e67e22;")

        QTimer.singleShot(800, self._wait_for_ready)

    def _wait_for_ready(self, attempts: int = 0):
        if self._health_ok():
            self._refresh_status()
            if self.cfg.get("open_browser", True) and not self._browser_opened:
                self._browser_opened = True
                self.open_dashboard()
            self.tray.showMessage("CyberCafe Server", "Services started")
            return

        if attempts >= 30:
            self.api_status.setText("API: Failed to start")
            self.api_status.setStyleSheet("font-size: 15px; color: #c0392b;")
            QMessageBox.warning(
                self,
                "Server Error",
                "Could not start the API. Check PostgreSQL, .env, and server logs.",
            )
            return

        QTimer.singleShot(500, lambda: self._wait_for_ready(attempts + 1))

    def stop_services(self):
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread = None
            time.sleep(0.3)

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._browser_opened = False
        self._refresh_status()
        self.tray.showMessage("CyberCafe Server", "Services stopped")

    def open_dashboard(self):
        webbrowser.open(self._dashboard_url())

    def _refresh_status(self):
        running = self._health_ok()
        if running:
            self.api_status.setText(f"API: Running on port {self._port()}")
            self.api_status.setStyleSheet("font-size: 15px; color: #2e7d32;")
            self.dashboard_status.setText(f"Dashboard: {self._dashboard_url()}")
            self.dashboard_status.setStyleSheet("font-size: 15px; color: #2e7d32;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif self.server_thread and self.server_thread.running:
            pass
        else:
            self.api_status.setText("API: Stopped")
            self.api_status.setStyleSheet("font-size: 15px; color: #c0392b;")
            self.dashboard_status.setText("Dashboard: Stopped")
            self.dashboard_status.setStyleSheet("font-size: 15px; color: #c0392b;")
            if not (self.server_thread and self.server_thread.is_alive()):
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

    def _save_options(self):
        self.cfg["auto_start"] = self.auto_start_cb.isChecked()
        self.cfg["open_browser"] = self.open_browser_cb.isChecked()
        save_manager_config(self.cfg)

    def quit_app(self):
        self.stop_services()
        QApplication.quit()

    def closeEvent(self, event):
        if self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "CyberCafe Server",
                "Running in the tray. Double-click to show or use Stop from the menu.",
            )
        else:
            self.stop_services()
            event.accept()


if "--install-service" in sys.argv:
    from services.server_install import install_service

    ok, messages = install_service()
    for line in messages:
        print(line)
    sys.exit(0 if ok else 1)

if "--uninstall-service" in sys.argv:
    from services.server_install import uninstall_service

    ok, messages = uninstall_service()
    for line in messages:
        print(line)
    sys.exit(0 if ok else 1)


def launch_manager(app: QApplication):
    app.main_window = ServerManagerWindow()
    app.main_window.show()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CyberCafe Server")
    app.setOrganizationName("CyberCafe")

    guard = QtSingleInstanceGuard(
        "CyberCafeServerDesktop",
        on_activate=lambda: activate_application_window(),
    )
    if not guard.try_acquire():
        sys.exit(0)
    app._instance_guard = guard

    app.setStyleSheet("""
        QMainWindow, QWidget { background: #f5f5f5; color: #222; }
        QGroupBox { font-weight: bold; margin-top: 8px; }
        QPushButton { border-radius: 4px; font-weight: bold; }
    """)

    apply_env_to_process()
    force_setup = "--setup" in sys.argv

    if force_setup or not is_configured():
        from ui.setup_wizard import ServerSetupWizard

        app.setup_wizard = ServerSetupWizard(on_complete=lambda: launch_manager(app))
        app.setup_wizard.show()
    else:
        launch_manager(app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
