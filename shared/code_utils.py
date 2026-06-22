"""Normalize access and master codes for lookup."""

from __future__ import annotations


def normalize_ticket_code(code: str) -> str:
    """Time/access ticket codes — letters and digits only, uppercase."""
    return "".join(ch for ch in code.upper() if ch.isalnum())


def normalize_master_code(code: str) -> str:
    """Master/static codes — uppercase, optional XXXX-XXXX-XXXX formatting."""
    raw = normalize_ticket_code(code)
    if len(raw) == 12:
        return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"
    return code.strip().upper()
