"""Helpers for PC.config JSON string storage."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def parse_pc_config(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def dump_pc_config(data: Dict[str, Any]) -> str:
    return json.dumps(data)


def pop_pending_commands(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    commands = config.pop("pending_commands", [])
    return commands if isinstance(commands, list) else []


def queue_command(config: Dict[str, Any], command: Dict[str, Any]) -> Dict[str, Any]:
    pending = config.get("pending_commands")
    if not isinstance(pending, list):
        pending = []
    pending.append(command)
    config["pending_commands"] = pending
    return config
