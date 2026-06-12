"""Ensure only one client process runs; raise the existing window on relaunch."""

from PyQt6.QtWidgets import QApplication

from shared.qt_single_instance import QtSingleInstanceGuard

SERVER_NAME = "CyberCafeClient"


class SingleInstanceGuard(QtSingleInstanceGuard):
    def __init__(self, on_activate=None):
        super().__init__(SERVER_NAME, on_activate=on_activate)


def activate_main_window():
    """Bring the running client UI to the foreground."""
    app = QApplication.instance()
    if app is None:
        return

    win = getattr(app, "main_window", None)
    if win is None:
        return

    session_mgr = getattr(win, "session_manager", None)
    if session_mgr and session_mgr.is_active and hasattr(win, "enter_session_mode"):
        win.enter_session_mode()
        return

    if hasattr(win, "show_lock_ui") and session_mgr is not None:
        win.show_lock_ui()
        return

    if hasattr(win, "showFullScreen"):
        win.showFullScreen()
    else:
        win.show()
    win.raise_()
    win.activateWindow()
