#!/usr/bin/env python3
"""Uninstall cleanup entry point bundled with the client installer."""

from __future__ import annotations

import sys
from pathlib import Path

CLIENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CLIENT_DIR.parent
for path in (str(REPO_ROOT), str(CLIENT_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from shared.system_cleanup import run_full_cleanup


def main() -> int:
    app_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else CLIENT_DIR
    watchdog_script = app_dir / "services" / "watchdog_service.py"
    _, messages = run_full_cleanup(
        app_dir=app_dir,
        watchdog_script=watchdog_script,
        skip_system=False,
    )
    for line in messages:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
