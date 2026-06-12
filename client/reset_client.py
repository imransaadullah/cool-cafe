#!/usr/bin/env python3
"""
Reset the CyberCafe client to factory defaults.

Removes local data files and undoes system changes made by setup:
  - config.json, session cache, offline queue, logs
  - Windows autostart registry entry (CyberCafeClient)
  - CyberCafe hosts-file DNS blocks
  - CyberCafeWatchdog Windows service (if installed)
  - Running CyberCafe client processes

Usage:
    python reset_client.py              # full reset (prompts for confirmation)
    python reset_client.py --yes        # skip confirmation
    python reset_client.py --files-only # only delete data files
    python main.py --reset --yes        # reset then start client

Run reset_client.bat as Administrator for full system cleanup.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

CLIENT_DIR = Path(__file__).resolve().parent
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))

from services.paths import app_path, get_app_dir

DATA_FILES = (
    "config.json",
    "session_cache.json",
    "paused_session.json",
    "offline_queue.json",
    "client.log",
    "filter_config.json",
    "blocked_processes.json",
)

EXTRA_LOG_FILES = (
    Path(__file__).resolve().parent / "services" / "watchdog.log",
)

HOSTS_MARKER = "# CyberCafe Block"
WATCHDOG_SERVICE = "CyberCafeWatchdog"
AUTOSTART_VALUE = "CyberCafeClient"


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


def get_data_file_paths() -> List[Path]:
    paths = [Path(app_path(name)) for name in DATA_FILES]
    paths.extend(path for path in EXTRA_LOG_FILES if path.exists())
    return paths


def remove_data_files() -> Tuple[int, List[str]]:
    removed = 0
    messages: List[str] = []

    for path in get_data_file_paths():
        if not path.exists():
            continue
        try:
            path.unlink()
            removed += 1
            messages.append(f"Removed file: {path}")
        except OSError as exc:
            messages.append(f"Failed to remove {path}: {exc}")

    return removed, messages


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

    # Dev mode: stop python/pythonw only when running this client's main.py
    ps_cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'client\\\\main\\.py' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stderr.strip() == "":
        messages.append("Stopped dev client processes (python main.py)")

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
    """Remove DisableTaskMgr if the installer or security setup set it."""
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
        messages.append("Flushed DNS cache")
    except PermissionError:
        messages.append(
            "Could not update hosts file — run as Administrator to remove DNS blocks"
        )
    except OSError as exc:
        messages.append(f"Could not update hosts file: {exc}")

    return messages


def remove_watchdog_service() -> List[str]:
    messages: List[str] = []
    if not is_windows():
        return messages

    watchdog_script = CLIENT_DIR / "services" / "watchdog_service.py"
    if watchdog_script.exists():
        for action in ("stop", "remove"):
            result = subprocess.run(
                [sys.executable, str(watchdog_script), action],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                messages.append(f"Watchdog service: {action} succeeded")
            elif action == "stop" and "1060" in (result.stderr or ""):
                pass
            elif "not installed" in (result.stdout + result.stderr).lower():
                pass

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
        else:
            messages.append(
                f"Could not remove service {WATCHDOG_SERVICE} — run as Administrator"
            )

    return messages


def reset_system_changes(skip_system: bool) -> List[str]:
    if skip_system:
        return ["Skipped system cleanup (--files-only)"]

    messages: List[str] = []
    messages.extend(kill_client_processes())
    messages.extend(remove_autostart_registry())
    messages.extend(reset_task_manager_policy())
    messages.extend(clean_hosts_file())
    messages.extend(remove_watchdog_service())

    if is_windows() and not is_admin():
        messages.append(
            "Note: Not running as Administrator — some system items may not have been removed. "
            "Right-click reset_client.bat and choose 'Run as administrator' for a full reset."
        )

    return messages


def print_plan(files_only: bool) -> None:
    print(f"App directory: {get_app_dir()}\n")
    print("Data files to remove:")
    found = False
    for path in get_data_file_paths():
        if path.exists():
            print(f"  - {path}")
            found = True
    if not found:
        print("  (none found)")

    if files_only:
        print("\nSystem cleanup: skipped (--files-only)")
        return

    print("\nSystem cleanup:")
    print("  - Stop CyberCafe client processes")
    print("  - Remove Windows autostart (CyberCafeClient)")
    print("  - Reset DisableTaskMgr policy (if set)")
    print("  - Remove CyberCafe DNS blocks from hosts file")
    print("  - Stop and remove CyberCafeWatchdog service")


def reset_client(skip_confirm: bool = False, files_only: bool = False) -> bool:
    print_plan(files_only)

    if not skip_confirm:
        scope = "data files only" if files_only else "all client data and system changes"
        answer = input(f"\nReset {scope}? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Reset cancelled.")
            return False

    print()
    file_count, file_messages = remove_data_files()
    system_messages = reset_system_changes(skip_system=files_only)

    for line in file_messages + system_messages:
        print(line)

    print()
    if file_count == 0 and not any(
        "Removed" in msg or "succeeded" in msg or "Stopped" in msg
        for msg in file_messages + system_messages
    ):
        print("Nothing to reset — client is already clean.")
    else:
        print("Reset complete.")

    print("Run the client again to start the setup wizard.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Reset CyberCafe client data and system changes",
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    parser.add_argument(
        "--files-only",
        action="store_true",
        help="Only remove data files, skip registry/hosts/service cleanup",
    )
    args = parser.parse_args()
    success = reset_client(skip_confirm=args.yes, files_only=args.files_only)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
