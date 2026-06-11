import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.lock_screen import LockScreen
from services.config_manager import client_config

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CyberCafe Client")
    app.setOrganizationName("CyberCafe")
    
    # Get UI settings from config
    theme = client_config.get("ui.theme", "dark")
    
    # Set application-wide style
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
    
    # Create and show lock screen
    lock_screen = LockScreen()
    
    # Set window flags based on config
    if client_config.get("ui.always_on_top", True):
        lock_screen.setWindowFlags(
            lock_screen.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
    
    if client_config.get("ui.fullscreen", True):
        lock_screen.showFullScreen()
    else:
        lock_screen.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
