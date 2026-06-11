import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.lock_screen import LockScreen
from ui.setup_wizard import SetupWizard, check_first_run
from services.config_manager import client_config

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def apply_theme(app, theme="dark"):
    """Apply the application theme."""
    if theme == "dark":
        app.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #16213e;
                border-radius: 5px;
                background-color: #0f3460;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #e94560;
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                background-color: #e94560;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c73e54;
            }
            QPushButton:pressed {
                background-color: #a33547;
            }
        """)
    else:
        app.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #cccccc;
                border-radius: 5px;
                background-color: #ffffff;
                color: #333333;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #007bff;
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                background-color: #007bff;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004094;
            }
        """)


def show_lock_screen(app):
    """Create and show the lock screen."""
    theme = client_config.get("ui.theme", "dark")
    apply_theme(app, theme)

    lock_screen = LockScreen()

    if client_config.get("ui.always_on_top", True):
        lock_screen.setWindowFlags(
            lock_screen.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

    if client_config.get("ui.fullscreen", True):
        lock_screen.showFullScreen()
    else:
        lock_screen.show()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CyberCafe Client")
    app.setOrganizationName("CyberCafe")

    if check_first_run():
        wizard = SetupWizard()
        wizard.lock_screen_callback = lambda: show_lock_screen(app)
        wizard.show()
    else:
        show_lock_screen(app)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
