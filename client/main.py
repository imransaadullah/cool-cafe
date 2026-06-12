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
            QWidget {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QMainWindow {
                background-color: #1a1a2e;
            }
            QStackedWidget {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
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
            QSpinBox {
                padding: 6px;
                border: 2px solid #16213e;
                border-radius: 5px;
                background-color: #0f3460;
                color: #ffffff;
            }
            QCheckBox {
                color: #ffffff;
                background-color: transparent;
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
            QDialog {
                background-color: #1a1a2e;
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

    # Must keep a reference on the app object — a local variable is garbage-
    # collected as soon as this function returns, which closes the window.
    app.main_window = LockScreen()

    if client_config.get("ui.always_on_top", True):
        app.main_window.setWindowFlags(
            app.main_window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

    if client_config.get("ui.fullscreen", True):
        app.main_window.showFullScreen()
    else:
        app.main_window.show()

    app.main_window.raise_()
    app.main_window.activateWindow()


def main():
    if "--reset" in sys.argv:
        from reset_client import reset_client
        reset_client(skip_confirm="--yes" in sys.argv or "-y" in sys.argv)
        sys.argv = [arg for arg in sys.argv if arg not in ("--reset", "--yes", "-y")]

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("CyberCafe Client")
        app.setOrganizationName("CyberCafe")

        theme = client_config.get("ui.theme", "dark")
        apply_theme(app, theme)

        if check_first_run():
            app.main_window = SetupWizard()
            app.main_window.lock_screen_callback = lambda: show_lock_screen(app)
            app.main_window.show()
            app.main_window.raise_()
            app.main_window.activateWindow()
        else:
            show_lock_screen(app)

        sys.exit(app.exec())
    except Exception:
        import traceback
        traceback.print_exc()
        if "--debug" not in sys.argv:
            print("\nRun with --debug for details, or check client.log")
        raise


if __name__ == "__main__":
    main()
