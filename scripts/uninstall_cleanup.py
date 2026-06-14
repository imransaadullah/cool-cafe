#!/usr/bin/env python3
"""Run full CyberCafe client cleanup during uninstall."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.system_cleanup import run_full_cleanup


def main() -> int:
    app_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "client"
    watchdog_script = app_dir / "services" / "watchdog_service.py"
    if not watchdog_script.exists():
        watchdog_script = REPO_ROOT / "client" / "services" / "watchdog_service.py"

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
