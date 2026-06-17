"""
Install/remove CyberCafe watchdog service and Windows autostart.
Used by setup wizard, CLI flags, and the Inno installer.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from services.paths import get_app_dir

WATCHDOG_SERVICE = "CyberCafeWatchdog"
AUTOSTART_VALUE = "CyberCafeClient"


def _app_dir() -> Path:
    return Path(get_app_dir())


def _watchdog_exe() -> Path:
    app = _app_dir()
    candidates = [
        app / "CyberCafeWatchdog.exe",
        app / "services" / "watchdog_service.py",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _client_exe() -> Path:
    app = _app_dir()
    candidates = [
        app / "CyberCafe Client.exe",
        app / "main.py",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def install_watchdog() -> Tuple[bool, List[str]]:
    """Register and start the watchdog Windows service."""
    messages: List[str] = []
    if sys.platform != "win32":
        return False, ["Watchdog service is only supported on Windows"]

    watchdog = _watchdog_exe()
    if not watchdog.exists():
        return False, [f"Watchdog executable not found: {watchdog}"]

    try:
        if watchdog.suffix.lower() == ".py":
            cmd = [sys.executable, str(watchdog), "install"]
        else:
            cmd = [str(watchdog), "install"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            messages.append(result.stderr.strip() or result.stdout.strip() or "install failed")
            return False, messages
        messages.append("Watchdog service installed")

        if watchdog.suffix.lower() == ".py":
            start_cmd = [sys.executable, str(watchdog), "start"]
        else:
            start_cmd = [str(watchdog), "start"]
        subprocess.run(start_cmd, capture_output=True, text=True)
        messages.append("Watchdog service started")
        return True, messages
    except Exception as exc:
        return False, [str(exc)]


def uninstall_watchdog() -> Tuple[bool, List[str]]:
    """Stop and remove the watchdog Windows service."""
    messages: List[str] = []
    if sys.platform != "win32":
        return True, messages

    watchdog = _watchdog_exe()
    try:
        if watchdog.exists():
            if watchdog.suffix.lower() == ".py":
                subprocess.run(
                    [sys.executable, str(watchdog), "stop"],
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    [sys.executable, str(watchdog), "remove"],
                    capture_output=True,
                    text=True,
                )
            else:
                subprocess.run([str(watchdog), "stop"], capture_output=True, text=True)
                subprocess.run([str(watchdog), "remove"], capture_output=True, text=True)
            messages.append("Watchdog service removed")
        else:
            subprocess.run(
                ["sc", "stop", WATCHDOG_SERVICE],
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["sc", "delete", WATCHDOG_SERVICE],
                capture_output=True,
                text=True,
            )
            messages.append("Watchdog service removed (sc)")
        return True, messages
    except Exception as exc:
        return False, [str(exc)]


def install_autostart() -> Tuple[bool, List[str]]:
    """Add client to HKLM Run key for boot autostart."""
    messages: List[str] = []
    if sys.platform != "win32":
        return False, ["Autostart is only supported on Windows"]

    client = _client_exe()
    if not client.exists():
        return False, [f"Client executable not found: {client}"]

    import winreg

    value = f'"{client}"'
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, AUTOSTART_VALUE, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        messages.append("Autostart enabled")
        return True, messages
    except PermissionError:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, AUTOSTART_VALUE, 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)
            messages.append("Autostart enabled (current user)")
            return True, messages
        except Exception as exc:
            return False, [str(exc)]
    except Exception as exc:
        return False, [str(exc)]


def remove_autostart() -> Tuple[bool, List[str]]:
    """Remove client from Windows Run keys."""
    messages: List[str] = []
    if sys.platform != "win32":
        return True, messages

    import winreg

    for hive_name, hive in (
        ("HKLM", winreg.HKEY_LOCAL_MACHINE),
        ("HKCU", winreg.HKEY_CURRENT_USER),
    ):
        try:
            key = winreg.OpenKey(
                hive,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, AUTOSTART_VALUE)
                messages.append(f"Autostart removed ({hive_name})")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass
    return True, messages


def apply_security_options(
    run_as_service: bool,
    auto_start_enabled: bool,
) -> List[str]:
    """Apply watchdog and autostart based on setup wizard choices."""
    messages: List[str] = []
    if auto_start_enabled:
        ok, lines = install_autostart()
        messages.extend(lines)
        if not ok:
            messages.append("Warning: autostart could not be enabled")
    else:
        remove_autostart()

    if run_as_service:
        ok, lines = install_watchdog()
        messages.extend(lines)
        if not ok:
            messages.append("Warning: watchdog service could not be installed")
    return messages
