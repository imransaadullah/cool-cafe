"""Installation paths and first-run detection for the server manager."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]


def env_path() -> Path:
    return get_app_dir() / ".env"


def setup_marker_path() -> Path:
    return get_app_dir() / "setup_complete.json"


def manager_config_path() -> Path:
    return get_app_dir() / "server_manager.json"


def is_configured() -> bool:
    """True when .env exists and setup has completed successfully."""
    if not env_path().is_file():
        return False
    marker = setup_marker_path()
    if not marker.is_file():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return bool(data.get("completed"))
    except Exception:
        return False


def mark_setup_complete(meta: Optional[Dict[str, Any]] = None) -> None:
    payload = {"completed": True, **(meta or {})}
    setup_marker_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_setup_meta() -> Dict[str, Any]:
    if not setup_marker_path().is_file():
        return {}
    try:
        return json.loads(setup_marker_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def find_prisma_schema() -> Optional[Path]:
    app = get_app_dir()
    candidates = [
        app / "prisma" / "schema.prisma",
        app.parent / "prisma" / "schema.prisma",
        Path(__file__).resolve().parents[2] / "prisma" / "schema.prisma",
    ]
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        candidates.insert(0, Path(sys._MEIPASS) / "prisma" / "schema.prisma")
    for path in candidates:
        if path.is_file():
            return path.parent
    return None


def apply_env_to_process(env_file: Optional[Path] = None) -> None:
    """Load .env key/value pairs into os.environ for child processes."""
    path = env_file or env_path()
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
