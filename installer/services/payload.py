"""Locate bundled installer payloads (dev tree or PyInstaller bundle)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

ROLE_LOCAL = "local_server"
ROLE_GLOBAL = "global_server"
ROLE_CLIENT = "client"

ROLE_LABELS = {
    ROLE_LOCAL: "Local Server",
    ROLE_GLOBAL: "Global Server",
    ROLE_CLIENT: "Client PC",
}

ROLE_DESCRIPTIONS = {
    ROLE_LOCAL: "Café branch server with dashboard, database setup, and PC management.",
    ROLE_GLOBAL: "Multi-site owner hub for syncing branches and central reporting.",
    ROLE_CLIENT: "Kiosk client for gaming PCs — lock screen, sessions, and watchdog.",
}

DEFAULT_DIRS = {
    ROLE_LOCAL: r"C:\Program Files\CyberCafe Local Server",
    ROLE_GLOBAL: r"C:\Program Files\CyberCafe Global Server",
    ROLE_CLIENT: r"C:\Program Files\CyberCafe Client",
}

MAIN_EXE = {
    ROLE_LOCAL: "CyberCafe Server.exe",
    ROLE_GLOBAL: "CyberCafe Global Server.exe",
    ROLE_CLIENT: "CyberCafe Client.exe",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def payload_root() -> Optional[Path]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "payload")
        candidates.append(Path(sys.executable).parent / "payload")
    candidates.append(repo_root() / "deploy" / "installer" / "payload")

    for path in candidates:
        if path.is_dir() and any((path / role).is_dir() for role in (ROLE_LOCAL, ROLE_GLOBAL, ROLE_CLIENT)):
            return path
    return None


def role_payload(role: str) -> Optional[Path]:
    root = payload_root()
    if not root:
        return None
    path = root / role
    return path if path.is_dir() else None
