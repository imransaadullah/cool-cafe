"""Shared client system cleanup used by reset and uninstall."""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

HOSTS_MARKER = "# CyberCafe Block"
WATCHDOG_SERVICE = "CyberCafeWatchdog"
AUTOSTART_VALUE = "CyberCafeClient"

DEFAULT_DATA_FILES = (
    "config.json",
    "session_cache.json",
    "paused_session.json",
    "offline_queue.json",
    "client.log",
    "filter_config.json",
    "blocked_processes.json",
    "master_code_cache.json",
)


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def kill_client_processes() -> List[str]:
    messages: List[str] = []
    if not is_windows():
        return messages

    result = subprocess.run(
        ["taskkill", "/F", "/IM", "CyberCafe Client.exe"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        messages.append("Stopped process: CyberCafe Client.exe")

    ps_cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'client\\\\main\\.py' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
    )
    return messages


def remove_autostart_registry() -> List[str]:
    messages: List[str] = []
    if not is_windows():
        return messages

    import winreg

    targets = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", AUTOSTART_VALUE),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", AUTOSTART_VALUE),
    ]

    for hive, subkey, value_name in targets:
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, value_name)
                hive_name = "HKLM" if hive == winreg.HKEY_LOCAL_MACHINE else "HKCU"
                messages.append(f"Removed autostart registry: {hive_name}\\{subkey}\\{value_name}")
        except FileNotFoundError:
            pass
        except OSError as exc:
            messages.append(f"Could not remove autostart ({value_name}): {exc}")

    return messages


def reset_task_manager_policy() -> List[str]:
    messages: List[str] = []
    if not is_windows():
        return messages

    import winreg

    subkey = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, "DisableTaskMgr")
            messages.append("Removed registry policy: DisableTaskMgr")
    except FileNotFoundError:
        pass
    except OSError as exc:
        messages.append(f"Could not reset DisableTaskMgr: {exc}")

    return messages


def clean_hosts_file() -> List[str]:
    messages: List[str] = []
    if not is_windows():
        return messages

    hosts_path = Path(r"C:\Windows\System32\drivers\etc\hosts")
    if not hosts_path.exists():
        return messages

    try:
        content = hosts_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        messages.append(f"Could not read hosts file: {exc}")
        return messages

    original_lines = content.splitlines()
    kept_lines = [line for line in original_lines if HOSTS_MARKER not in line]

    if len(kept_lines) == len(original_lines):
        return messages

    removed_count = len(original_lines) - len(kept_lines)
    try:
        hosts_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
        messages.append(f"Removed {removed_count} CyberCafe block(s) from hosts file")
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
    except PermissionError:
        messages.append("Could not update hosts file — run as Administrator")
    except OSError as exc:
        messages.append(f"Could not update hosts file: {exc}")

    return messages


def remove_watchdog_service(watchdog_script: Path | None = None) -> List[str]:
    messages: List[str] = []
    if not is_windows():
        return messages

    if watchdog_script and watchdog_script.exists():
        for action in ("stop", "remove"):
            result = subprocess.run(
                [sys.executable, str(watchdog_script), action],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                messages.append(f"Watchdog service: {action} succeeded")

    result = subprocess.run(
        ["sc", "query", WATCHDOG_SERVICE],
        capture_output=True,
        text=True,
    )
    if "SERVICE_NAME" in result.stdout:
        subprocess.run(["sc", "stop", WATCHDOG_SERVICE], capture_output=True)
        delete = subprocess.run(
            ["sc", "delete", WATCHDOG_SERVICE],
            capture_output=True,
            text=True,
        )
        if delete.returncode == 0:
            messages.append(f"Removed Windows service: {WATCHDOG_SERVICE}")

    return messages


def remove_data_files(app_dir: Path, extra_files: Tuple[Path, ...] = ()) -> Tuple[int, List[str]]:
    removed = 0
    messages: List[str] = []

    paths = [app_dir / name for name in DEFAULT_DATA_FILES]
    paths.extend(extra_files)

    for path in paths:
        if not path.exists():
            continue
        try:
            path.unlink()
            removed += 1
            messages.append(f"Removed file: {path}")
        except OSError as exc:
            messages.append(f"Failed to remove {path}: {exc}")

    return removed, messages


def run_full_cleanup(
    app_dir: Path,
    extra_files: Tuple[Path, ...] = (),
    watchdog_script: Path | None = None,
    skip_system: bool = False,
) -> Tuple[int, List[str]]:
    file_count, file_messages = remove_data_files(app_dir, extra_files)
    system_messages: List[str] = []

    if not skip_system:
        system_messages.extend(kill_client_processes())
        system_messages.extend(remove_autostart_registry())
        system_messages.extend(reset_task_manager_policy())
        system_messages.extend(clean_hosts_file())
        system_messages.extend(remove_watchdog_service(watchdog_script))

        if is_windows() and not is_admin():
            system_messages.append(
                "Note: Not running as Administrator — some system items may not have been removed."
            )

    return file_count, file_messages + system_messages
