"""Copy payloads, shortcuts, autostart, and post-install launch."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .payload import MAIN_EXE, ROLE_CLIENT, ROLE_GLOBAL, ROLE_LOCAL

VALID_ROLES = {ROLE_LOCAL, ROLE_GLOBAL, ROLE_CLIENT}

LogFn = Callable[[str], None]


def _log(log: Optional[LogFn], msg: str) -> None:
    if log:
        log(msg)


def copy_role_payload(
    source: Path,
    dest: Path,
    log: Optional[LogFn] = None,
) -> Tuple[bool, str]:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            _log(log, f"Removing existing install at {dest}")
            shutil.rmtree(dest)
        _log(log, f"Copying files to {dest}…")
        shutil.copytree(source, dest)
        return True, str(dest)
    except PermissionError:
        return False, (
            f"Permission denied writing to {dest}. "
            "Close any running CyberCafe apps and try again, or run the installer as Administrator."
        )
    except Exception as exc:
        return False, str(exc)


def create_desktop_shortcut(name: str, target: Path) -> List[str]:
    messages: List[str] = []
    if sys.platform != "win32" or not target.is_file():
        return messages
    desktop = Path.home() / "Desktop"
    shortcut = desktop / f"{name}.lnk"
    ps = (
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut}');"
        f"$s.TargetPath = '{target}';"
        f"$s.WorkingDirectory = '{target.parent}';"
        f"$s.Save()"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        messages.append(f"Desktop shortcut: {name}")
    return messages


def set_autostart(value_name: str, exe: Path) -> List[str]:
    messages: List[str] = []
    if sys.platform != "win32" or not exe.is_file():
        return messages
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        messages.append("Autostart enabled")
    except Exception as exc:
        messages.append(f"Autostart skipped: {exc}")
    return messages


def install_client_watchdog(install_dir: Path, log: Optional[LogFn] = None) -> List[str]:
    messages: List[str] = []
    watchdog = install_dir / "CyberCafeWatchdog.exe"
    if not watchdog.is_file():
        return messages
    for args in (["install"], ["start"]):
        _log(log, f"Watchdog: {' '.join(args)}")
        subprocess.run([str(watchdog), *args], capture_output=True, text=True)
    messages.append("Watchdog service installed")
    return messages


def run_install(
    role: str,
    source: Path,
    dest: Path,
    *,
    desktop_shortcut: bool = True,
    autostart: bool = True,
    client_watchdog: bool = True,
    log: Optional[LogFn] = None,
) -> Tuple[bool, str, Optional[Path]]:
    if role not in VALID_ROLES:
        return False, f"Unknown installation type: {role!r}", None

    ok, msg = copy_role_payload(source, dest, log=log)
    if not ok:
        return False, msg, None

    exe_name = MAIN_EXE[role]
    main_exe = dest / exe_name
    if not main_exe.is_file():
        return False, f"Install incomplete: missing {exe_name}", None

    label = exe_name.replace(".exe", "")
    if desktop_shortcut:
        for line in create_desktop_shortcut(label, main_exe):
            _log(log, line)

    if autostart:
        reg_name = {
            ROLE_LOCAL: "CyberCafeLocalServer",
            ROLE_GLOBAL: "CyberCafeGlobalServer",
            ROLE_CLIENT: "CyberCafeClient",
        }.get(role, "CyberCafeApp")
        for line in set_autostart(reg_name, main_exe):
            _log(log, line)

    if role == ROLE_CLIENT and client_watchdog:
        for line in install_client_watchdog(dest, log=log):
            _log(log, line)
        if autostart:
            subprocess.run(
                [str(main_exe), "--install-autostart"],
                capture_output=True,
                text=True,
                cwd=str(dest),
            )

    _log(log, "Installation complete.")
    return True, msg, main_exe


def launch_application(exe: Path) -> None:
    if exe.is_file():
        subprocess.Popen(
            [str(exe)],
            cwd=str(exe.parent),
            creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
        )
