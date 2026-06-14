"""Discover installed and runnable applications on the client PC."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

EXE_PATTERN = re.compile(r"([^\\/\s]+\.exe)", re.IGNORECASE)


def normalize_exe_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip().strip('"')
    if not text:
        return None
    match = EXE_PATTERN.search(text)
    if match:
        return match.group(1).lower()
    if text.lower().endswith(".exe"):
        return Path(text).name.lower()
    return None


def _merge_app(
    apps: Dict[str, Dict[str, Any]],
    name: str,
    exe_path: Optional[str],
    source: str,
) -> None:
    exe_name = normalize_exe_name(exe_path)
    if not exe_name:
        return

    display_name = (name or exe_name).strip()
    if not display_name:
        display_name = exe_name

    existing = apps.get(exe_name)
    entry = {
        "name": display_name,
        "exe_name": exe_name,
        "path": exe_path or "",
        "source": source,
    }
    if not existing or len(display_name) > len(existing["name"]):
        apps[exe_name] = entry


def _scan_registry_apps(apps: Dict[str, Dict[str, Any]]) -> None:
    if platform.system().lower() != "windows":
        return

    import winreg

    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, subkey in roots:
        try:
            with winreg.OpenKey(hive, subkey) as root:
                for index in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        app_key_name = winreg.EnumKey(root, index)
                        with winreg.OpenKey(root, app_key_name) as app_key:
                            display_name = _read_reg_str(app_key, "DisplayName")
                            if not display_name:
                                continue
                            if _read_reg_dword(app_key, "SystemComponent") == 1:
                                continue
                            if _read_reg_dword(app_key, "ParentKeyName"):
                                continue

                            display_icon = _read_reg_str(app_key, "DisplayIcon")
                            install_location = _read_reg_str(app_key, "InstallLocation")
                            exe_path = display_icon or install_location
                            _merge_app(apps, display_name, exe_path, "registry")
                    except OSError:
                        continue
        except OSError:
            continue


def _read_reg_str(key, name: str) -> Optional[str]:
    import winreg

    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value).strip() if value else None
    except OSError:
        return None


def _read_reg_dword(key, name: str) -> Optional[int]:
    import winreg

    try:
        value, _ = winreg.QueryValueEx(key, name)
        return int(value)
    except OSError:
        return None


def _scan_start_menu_apps(apps: Dict[str, Dict[str, Any]]) -> None:
    if platform.system().lower() != "windows":
        return

    ps_script = r"""
$apps = @()
$roots = @(
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs",
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
)
$shell = New-Object -ComObject WScript.Shell
foreach ($root in $roots) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem -Path $root -Filter *.lnk -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $shortcut = $shell.CreateShortcut($_.FullName)
            $target = $shortcut.TargetPath
            if ($target -and $target.ToLower().EndsWith('.exe')) {
                $apps += [PSCustomObject]@{
                    name = $_.BaseName
                    path = $target
                }
            }
        } catch {}
    }
}
$apps | ConvertTo-Json -Compress
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return
        payload = json.loads(result.stdout)
        if isinstance(payload, dict):
            payload = [payload]
        for item in payload:
            _merge_app(
                apps,
                str(item.get("name") or ""),
                str(item.get("path") or ""),
                "start_menu",
            )
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return


def _scan_running_apps(apps: Dict[str, Dict[str, Any]]) -> None:
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            info = proc.info
            exe_path = info.get("exe") or info.get("name")
            display_name = Path(str(exe_path)).stem if exe_path else ""
            _merge_app(apps, display_name, str(exe_path or ""), "running")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def scan_installed_apps(include_running: bool = True) -> List[Dict[str, Any]]:
    """Return deduplicated apps sorted by display name."""
    apps: Dict[str, Dict[str, Any]] = {}
    _scan_registry_apps(apps)
    _scan_start_menu_apps(apps)
    if include_running:
        _scan_running_apps(apps)
    return sorted(apps.values(), key=lambda item: item["name"].lower())
