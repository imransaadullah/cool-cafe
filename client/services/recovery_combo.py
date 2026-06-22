"""Parse and detect Alt + recovery key combinations."""

from __future__ import annotations

from typing import Iterable, Set

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from services.config_manager import client_config

_KEY_MAP: dict[str, Qt.Key] | None = None


def _build_key_map() -> dict[str, Qt.Key]:
    global _KEY_MAP
    if _KEY_MAP is not None:
        return _KEY_MAP

    mapping: dict[str, Qt.Key] = {}
    for index in range(1, 13):
        mapping[f"F{index}"] = getattr(Qt.Key, f"Key_F{index}")

    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        mapping[letter] = getattr(Qt.Key, f"Key_{letter}")

    for digit in "0123456789":
        mapping[digit] = getattr(Qt.Key, f"Key_{digit}")

    _KEY_MAP = mapping
    return mapping


def parse_recovery_combo(combo: str | Iterable[str] | None) -> list[str]:
    if combo is None:
        return []
    if isinstance(combo, str):
        if not combo.strip():
            return []
        return [part.strip().upper() for part in combo.split("+") if part.strip()]
    return [str(part).strip().upper() for part in combo if str(part).strip()]


def configured_recovery_combo() -> list[str]:
    return parse_recovery_combo(client_config.get("security.recovery_combo", ""))


def alt_is_held(event: QKeyEvent, pressed_keys: Set[int]) -> bool:
    modifiers = event.modifiers()
    if modifiers & (
        Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.AltGrModifier
    ):
        return True
    return Qt.Key.Key_Alt in pressed_keys or Qt.Key.Key_AltGr in pressed_keys


def recovery_combo_matches(
    event: QKeyEvent,
    pressed_keys: Set[int],
    recovery_keys: list[str],
) -> bool:
    if not recovery_keys:
        return False
    if not alt_is_held(event, pressed_keys):
        return False

    key_map = _build_key_map()
    for key_name in recovery_keys:
        qt_key = key_map.get(key_name.upper())
        if qt_key is None or qt_key not in pressed_keys:
            return False
    return True
