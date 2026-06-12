#!/usr/bin/env python3
"""
Check whether CyberCafe services are already running.

Exit codes (for batch launchers):
  0 = service already running (foreground window activated if possible)
  1 = service not running — caller should start it
  2 = unknown service name or error
"""

from __future__ import annotations

import argparse
import platform
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SERVICES = {
    "server": {
        "port": 8000,
        "health_url": "http://127.0.0.1:8000/api/health",
        "window_title": "CyberCafe Server",
    },
    "dashboard": {
        "port": 3000,
        "health_url": "http://127.0.0.1:3000",
        "window_title": "CyberCafe Dashboard",
    },
}

CLIENT_SOCKET = "CyberCafeClient"
DESKTOP_SOCKET = "CyberCafeServerDesktop"


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _service_running(name: str) -> bool:
    cfg = SERVICES[name]
    if _health_ok(cfg["health_url"]):
        return True
    return _port_open(cfg["port"])


def _activate_window(title: str) -> None:
    if platform.system().lower() != "windows":
        return
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$w = New-Object -ComObject WScript.Shell; "
                f"$null = $w.AppActivate('{title}')"
            ),
        ],
        capture_output=True,
        text=True,
    )


def _ping_qt_instance(server_name: str) -> bool:
    try:
        from PyQt6.QtWidgets import QApplication
        from shared.qt_single_instance import QtSingleInstanceGuard
    except ImportError:
        return False

    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication([])
        owns_app = True

    guard = QtSingleInstanceGuard(server_name)
    running = guard.ping_running_instance()

    if owns_app:
        app.quit()

    return running


def check_service(name: str) -> int:
    if name in SERVICES:
        if _service_running(name):
            _activate_window(SERVICES[name]["window_title"])
            print(f"{name.capitalize()} is already running - brought window to front.")
            return 0
        return 1

    if name == "client":
        if _ping_qt_instance(CLIENT_SOCKET):
            print("Client is already running - brought window to front.")
            return 0
        return 1

    if name == "desktop":
        if _ping_qt_instance(DESKTOP_SOCKET):
            print("Server desktop app is already running - brought window to front.")
            return 0
        return 1

    print(f"Unknown service: {name}", file=sys.stderr)
    return 2


def main():
    parser = argparse.ArgumentParser(description="CyberCafe service single-instance guard")
    parser.add_argument(
        "service",
        choices=["server", "dashboard", "client", "desktop"],
        help="Service to check",
    )
    args = parser.parse_args()
    sys.exit(check_service(args.service))


if __name__ == "__main__":
    main()
