"""
Application path helpers for dev and packaged (PyInstaller) runs.
"""

import os
import sys


def get_app_dir() -> str:
    """Return the directory where config and cache files should live."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_path(filename: str) -> str:
    """Return an absolute path for a file in the app directory."""
    return os.path.join(get_app_dir(), filename)
