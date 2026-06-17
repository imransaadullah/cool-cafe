"""Application-level guards to prevent exiting the client in production."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from services.config_manager import client_config


def install_app_kiosk_guard(app: QApplication) -> None:
    """Keep the process alive when windows are hidden during a session."""
    app.setQuitOnLastWindowClosed(False)


def should_block_window_close() -> bool:
    return client_config.is_production_mode() and not client_config.is_exit_allowed()


def should_block_quit_shortcut(event: QKeyEvent) -> bool:
    if client_config.is_exit_allowed():
        return False

    key = event.key()
    modifiers = event.modifiers()

    if key == Qt.Key.Key_F4 and modifiers & Qt.KeyboardModifier.AltModifier:
        return True
    if key == Qt.Key.Key_Q and modifiers & Qt.KeyboardModifier.ControlModifier:
        return True
    if key == Qt.Key.Key_W and modifiers & Qt.KeyboardModifier.ControlModifier:
        return True
    if key == Qt.Key.Key_Escape:
        return True

    return False
