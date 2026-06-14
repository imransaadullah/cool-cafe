#!/usr/bin/env python3
"""
Reset the CyberCafe client to factory defaults.

Removes local data files and undoes system changes made by setup.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CLIENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CLIENT_DIR.parent
for path in (str(REPO_ROOT), str(CLIENT_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from services.paths import app_path, get_app_dir
from shared.system_cleanup import (
    DEFAULT_DATA_FILES,
    is_admin,
    is_windows,
    run_full_cleanup,
)

EXTRA_LOG_FILES = (
    CLIENT_DIR / "services" / "watchdog.log",
)


def get_data_file_paths():
    paths = [Path(app_path(name)) for name in DEFAULT_DATA_FILES]
    paths.extend(path for path in EXTRA_LOG_FILES if path.exists())
    return paths


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
    app_dir = Path(get_app_dir())
    watchdog_script = CLIENT_DIR / "services" / "watchdog_service.py"
    file_count, messages = run_full_cleanup(
        app_dir=app_dir,
        extra_files=tuple(p for p in EXTRA_LOG_FILES if p.exists()),
        watchdog_script=watchdog_script,
        skip_system=files_only,
    )

    for line in messages:
        print(line)

    print()
    if file_count == 0 and not any(
        "Removed" in msg or "succeeded" in msg or "Stopped" in msg
        for msg in messages
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
