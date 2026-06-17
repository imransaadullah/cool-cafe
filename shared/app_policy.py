"""Merge branch-wide, filter-rule, and per-PC application policies."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

DEFAULT_BLOCKED_APPS = [
    "taskmgr.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "regedit.exe",
]

# Always permitted during enforcement (lowercase exe names)
SYSTEM_ALLOWLIST = {
    "system",
    "system idle process",
    "csrss.exe",
    "smss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "dwm.exe",
    "explorer.exe",
    "python.exe",
    "pythonw.exe",
    "cybercafe client.exe",
}


def _parse_json_config(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_apps(names: Optional[List[str]]) -> List[str]:
    if not names:
        return []
    return sorted({str(name).strip().lower() for name in names if str(name).strip()})


def _policy_from_source(source: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not source:
        return {}
    policy = source.get("app_policy") if isinstance(source.get("app_policy"), dict) else source
    return {
        "mode": policy.get("mode"),
        "allowed_apps": _normalize_apps(policy.get("allowed_apps")),
        "blocked_apps": _normalize_apps(policy.get("blocked_apps")),
    }


def rules_to_app_lists(filter_rules: List[Any]) -> Dict[str, List[str]]:
    allowed: List[str] = []
    blocked: List[str] = []
    for rule in filter_rules:
        rule_type = getattr(rule, "ruleType", None) or rule.get("rule_type")
        if rule_type != "process":
            continue
        pattern = getattr(rule, "pattern", None) or rule.get("pattern")
        action = getattr(rule, "action", None) or rule.get("action", "block")
        if not pattern:
            continue
        if action == "allow":
            allowed.append(str(pattern))
        else:
            blocked.append(str(pattern))
    return {
        "allowed_apps": _normalize_apps(allowed),
        "blocked_apps": _normalize_apps(blocked),
    }


def merge_app_policy(
    branch_config: Any = None,
    pc_config: Any = None,
    filter_rules: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Build effective app policy.

    Precedence (later wins for lists; mode from most specific source):
      defaults -> branch -> filter rules -> PC override
    """
    branch = _policy_from_source(_parse_json_config(branch_config))
    pc = _policy_from_source(_parse_json_config(pc_config))
    rules = rules_to_app_lists(filter_rules or [])

    mode = (
        pc.get("mode")
        or branch.get("mode")
        or "blocklist"
    )

    allowed = set()
    blocked = set(DEFAULT_BLOCKED_APPS)

    allowed.update(branch.get("allowed_apps", []))
    blocked.update(branch.get("blocked_apps", []))
    allowed.update(rules.get("allowed_apps", []))
    blocked.update(rules.get("blocked_apps", []))
    allowed.update(pc.get("allowed_apps", []))
    blocked.update(pc.get("blocked_apps", []))

    # PC blocked list replaces branch defaults when explicitly set
    if pc.get("blocked_apps"):
        blocked = set(pc.get("blocked_apps")) | set(DEFAULT_BLOCKED_APPS)

    return {
        "mode": mode if mode in ("blocklist", "allowlist", "hybrid") else "blocklist",
        "allowed_apps": sorted(allowed),
        "blocked_apps": sorted(blocked),
        "system_allowlist": sorted(SYSTEM_ALLOWLIST),
    }


def is_process_allowed(process_name: str, policy: Dict[str, Any]) -> bool:
    name = (process_name or "").strip().lower()
    if not name:
        return True

    system = {x.lower() for x in policy.get("system_allowlist", SYSTEM_ALLOWLIST)}
    if name in system:
        return True

    allowed = {x.lower() for x in policy.get("allowed_apps", [])}
    blocked = {x.lower() for x in policy.get("blocked_apps", [])}
    mode = policy.get("mode", "blocklist")

    if mode == "allowlist":
        return name in allowed
    if mode == "hybrid":
        if name in blocked:
            return False
        if allowed:
            return name in allowed
        return True
    # blocklist
    return name not in blocked


def resolve_client_mode(
    server_config: Optional[Dict[str, Any]] = None,
    local_mode: Optional[str] = None,
) -> str:
    """Server production mode always wins; local dev is for developer machines only."""
    server_mode = (server_config or {}).get("client_mode")
    if server_mode == "production":
        return "production"
    if local_mode == "dev":
        return "dev"
    if server_mode == "dev":
        return "dev"
    return "production"
