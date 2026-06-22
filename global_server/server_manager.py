"""CyberCafe Global Server Manager — start/stop owner API."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn
from PyQt6.QtCore import QTimer
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

GLOBAL_SERVER = Path(__file__).resolve().parent
ROOT = GLOBAL_SERVER.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GLOBAL_SERVER))

from shared.config import settings
from shared.qt_single_instance import QtSingleInstanceGuard, activate_application_window
from services.install_config import apply_env_to_process, is_configured


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return GLOBAL_SERVER


def load_manager_config() -> dict:
    path = get_app_dir() / "server_manager.json"
    defaults = {"auto_start": True, "open_browser": True, "host": "0.0.0.0", "port": 9000}
    if path.is_file():
        try:
            defaults.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return defaults


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None
        self.running = False

    def run(self):
        from global_server.app.main import app

        self.running = True
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        self.running = False
        if self.server:
            self.server.should_exit = True


class GlobalServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_manager_config()
        self.server_thread = None
        self.setWindowTitle("CyberCafe Global Server")
        self.setMinimumSize(480, 300)
        self._build_menu()
        self._build_ui()
        self._build_tray()
        self.poll = QTimer()
        self.poll.timeout.connect(self._refresh)
        self.poll.start(2000)
        if self.cfg.get("auto_start", True):
            QTimer.singleShot(500, self.start_services)

    def _build_menu(self):
        menu = self.menuBar().addMenu("Settings")
        act = QAction("Run Setup Wizard…", self)
        act.triggered.connect(self._open_setup)
        menu.addAction(act)

    def _open_setup(self):
        if self.server_thread and self.server_thread.running:
            QMessageBox.information(self, "Stop First", "Stop services before re-running setup.")
            return
        from ui.setup_wizard import GlobalSetupWizard

        self._wiz = GlobalSetupWizard(on_complete=self._after_setup)
        self._wiz.show()

    def _after_setup(self):
        apply_env_to_process()
        self.cfg = load_manager_config()
        if self.cfg.get("auto_start", True):
            self.start_services()

    def _build_ui(self):
        c = QWidget()
        self.setCentralWidget(c)
        lay = QVBoxLayout(c)
        lay.addWidget(QLabel("Global Server Manager"))
        box = QGroupBox("Status")
        bl = QVBoxLayout(box)
        self.status = QLabel("Stopped")
        bl.addWidget(self.status)
        lay.addWidget(box)
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_services)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_services)
        self.stop_btn.setEnabled(False)
        self.open_btn = QPushButton("Open API Docs")
        self.open_btn.clicked.connect(self.open_docs)
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.open_btn)
        lay.addLayout(row)
        lay.addStretch()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        m = QMenu()
        for label, slot in (
            ("Show", self.show),
            ("Start", self.start_services),
            ("Stop", self.stop_services),
            ("API Docs", self.open_docs),
        ):
            a = QAction(label, self)
            a.triggered.connect(slot)
            m.addAction(a)
        m.addSeparator()
        q = QAction("Quit", self)
        q.triggered.connect(self.quit_app)
        m.addAction(q)
        self.tray.setContextMenu(m)
        self.tray.show()

    def _port(self) -> int:
        return int(self.cfg.get("port", 9000))

    def _api_url(self) -> str:
        return f"http://127.0.0.1:{self._port()}"

    def _health(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self._api_url()}/api/health", timeout=2) as r:
                return r.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def start_services(self):
        if self.server_thread and self.server_thread.running:
            self.open_docs()
            return
        host = self.cfg.get("host", "0.0.0.0")
        port = self._port()
        self.server_thread = ServerThread(host, port)
        self.server_thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status.setText("Starting…")
        QTimer.singleShot(800, self._wait_ready)

    def _wait_ready(self, n=0):
        if self._health():
            self._refresh()
            if self.cfg.get("open_browser", True):
                self.open_docs()
            self.tray.showMessage("Global Server", "Started")
            return
        if n < 30:
            QTimer.singleShot(500, lambda: self._wait_ready(n + 1))

    def stop_services(self):
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread = None
            time.sleep(0.2)
        self._refresh()
        self.tray.showMessage("Global Server", "Stopped")

    def open_docs(self):
        webbrowser.open(f"{self._api_url()}/api/docs")

    def _refresh(self):
        if self._health():
            self.status.setText(f"Running — {self._api_url()}")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status.setText("Stopped")
            if not (self.server_thread and self.server_thread.is_alive()):
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

    def quit_app(self):
        self.stop_services()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("Global Server", "Running in tray.")


def launch_manager(app: QApplication):
    app.main_window = GlobalServerWindow()
    app.main_window.show()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CyberCafe Global Server")
    guard = QtSingleInstanceGuard("CyberCafeGlobalDesktop", on_activate=lambda: activate_application_window())
    if not guard.try_acquire():
        sys.exit(0)
    app._guard = guard
    apply_env_to_process()
    if "--setup" in sys.argv or not is_configured():
        from ui.setup_wizard import GlobalSetupWizard

        app._wiz = GlobalSetupWizard(on_complete=lambda: launch_manager(app))
        app._wiz.show()
    else:
        launch_manager(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
