"""Install/remove CyberCafe server Windows service."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

SERVICE_NAME = "CyberCafeServer"


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]


def _service_exe() -> Path:
    app = _app_dir()
    for name in ("CyberCafeServerService.exe", "services/server_service.py"):
        path = app / name
        if path.exists():
            return path
    return app / "CyberCafeServerService.exe"


def install_service() -> Tuple[bool, List[str]]:
    messages: List[str] = []
    if sys.platform != "win32":
        return False, ["Windows service install is only supported on Windows"]

    exe = _service_exe()
    if not exe.exists():
        return False, [f"Service executable not found: {exe}"]

    try:
        if exe.suffix.lower() == ".py":
            cmd = [sys.executable, str(exe), "install"]
            start_cmd = [sys.executable, str(exe), "start"]
        else:
            cmd = [str(exe), "install"]
            start_cmd = [str(exe), "start"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, [result.stderr.strip() or result.stdout.strip() or "install failed"]
        messages.append("Server service installed")
        subprocess.run(start_cmd, capture_output=True, text=True)
        messages.append("Server service started")
        return True, messages
    except Exception as exc:
        return False, [str(exc)]


def uninstall_service() -> Tuple[bool, List[str]]:
    messages: List[str] = []
    if sys.platform != "win32":
        return True, messages

    exe = _service_exe()
    try:
        if exe.exists():
            if exe.suffix.lower() == ".py":
                subprocess.run([sys.executable, str(exe), "stop"], capture_output=True, text=True)
                subprocess.run([sys.executable, str(exe), "remove"], capture_output=True, text=True)
            else:
                subprocess.run([str(exe), "stop"], capture_output=True, text=True)
                subprocess.run([str(exe), "remove"], capture_output=True, text=True)
            messages.append("Server service removed")
        else:
            subprocess.run(["sc", "stop", SERVICE_NAME], capture_output=True, text=True)
            subprocess.run(["sc", "delete", SERVICE_NAME], capture_output=True, text=True)
        return True, messages
    except Exception as exc:
        return False, [str(exc)]
