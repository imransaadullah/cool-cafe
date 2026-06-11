"""
Alarm Service
Handles alarm triggers, sound, and blank screen
"""

import sys
import time
import threading
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from services.config_manager import client_config


class AlarmScreen(QMainWindow):
    """Fullscreen alarm screen that blocks all input."""
    
    alarm_dismissed = pyqtSignal()
    
    def __init__(self, recovery_combo: list, alarm_color: str = "#FF0000"):
        super().__init__()
        self.recovery_combo = recovery_combo
        self.alarm_color = alarm_color
        self.pressed_keys = set()
        self.is_playing = True
        
        # Setup UI
        self.setup_ui()
        
        # Start alarm sound in separate thread
        self.sound_thread = threading.Thread(target=self._play_alarm_sound, daemon=True)
        self.sound_thread.start()
    
    def setup_ui(self):
        """Setup the alarm screen UI."""
        self.setWindowTitle("SECURITY ALARM")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Set background color
        self.setStyleSheet(f"background-color: {self.alarm_color};")
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Warning text
        warning_label = QLabel("⚠ SECURITY BREACH ⚠")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        warning_label.setStyleSheet("color: white;")
        layout.addWidget(warning_label)
        
        # Instructions
        instructions = QLabel("Contact administrator to dismiss")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setFont(QFont("Arial", 24))
        instructions.setStyleSheet("color: white;")
        layout.addWidget(instructions)
        
        # Recovery combo display
        combo_text = " + ".join(["Alt"] + self.recovery_combo)
        combo_label = QLabel(f"Recovery: {combo_text}")
        combo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        combo_label.setFont(QFont("Arial", 18))
        combo_label.setStyleSheet("color: white;")
        layout.addWidget(combo_label)
        
        # Block focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def keyPressEvent(self, event):
        """Handle key press for recovery combo."""
        key = event.key()
        self.pressed_keys.add(key)
        
        # Check if recovery combo pressed
        if self._check_recovery_combo():
            self._dismiss_alarm()
            return
        
        # Block everything else
        event.accept()
    
    def keyReleaseEvent(self, event):
        """Handle key release."""
        self.pressed_keys.discard(event.key())
    
    def _check_recovery_combo(self) -> bool:
        """Check if Alt + recovery keys pressed."""
        # Check Alt key
        if Qt.Key.Key_Alt not in self.pressed_keys:
            return False
        
        # Check all recovery keys
        key_map = {
            "F1": Qt.Key.Key_F1, "F2": Qt.Key.Key_F2, "F3": Qt.Key.Key_F3,
            "F4": Qt.Key.Key_F4, "F5": Qt.Key.Key_F5, "F6": Qt.Key.Key_F6,
            "F7": Qt.Key.Key_F7, "F8": Qt.Key.Key_F8, "F9": Qt.Key.Key_F9,
            "F10": Qt.Key.Key_F10, "F11": Qt.Key.Key_F11, "F12": Qt.Key.Key_F12,
        }
        
        # Add letter keys
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            key_map[letter] = getattr(Qt.Key, f"Key_{letter}")
        
        # Add number keys
        for num in "0123456789":
            key_map[num] = getattr(Qt.Key, f"Key_{num}")
        
        for key_name in self.recovery_combo:
            if key_name not in key_map:
                return False
            if key_map[key_name] not in self.pressed_keys:
                return False
        
        return True
    
    def _dismiss_alarm(self):
        """Dismiss the alarm."""
        self.is_playing = False
        self.alarm_dismissed.emit()
        self.close()
    
    def _play_alarm_sound(self):
        """Play alarm sound that bypasses system mute."""
        try:
            if sys.platform == "win32":
                import ctypes
                # Use Windows MessageBeep which bypasses mute
                while self.is_playing:
                    ctypes.windll.user32.MessageBeep(0x00000010)  # MB_ICONHAND
                    time.sleep(0.5)
            else:
                # Fallback for other platforms
                import os
                while self.is_playing:
                    os.system("echo -n '\\a'")  # Bell character
                    time.sleep(0.5)
        except Exception:
            # If sound fails, just continue
            pass
    
    def mousePressEvent(self, event):
        """Block mouse clicks."""
        event.accept()
    
    def closeEvent(self, event):
        """Prevent closing."""
        if self.is_playing:
            event.ignore()
        else:
            event.accept()


class AlarmService:
    """Service to manage alarm triggers."""
    
    def __init__(self):
        self.alarm_screen = None
        self.wrong_attempts = 0
        self.max_attempts = 3
    
    def trigger_alarm(self, reason: str):
        """Trigger the alarm."""
        # Get recovery combo
        recovery_combo = client_config.get("security.recovery_combo", "F9+F10+F11").split("+")
        
        # Get alarm color
        alarm_color = client_config.get("security.alarm_color", "#FF0000")
        
        # Create and show alarm screen
        self.alarm_screen = AlarmScreen(recovery_combo, alarm_color)
        self.alarm_screen.alarm_dismissed.connect(self._on_alarm_dismissed)
        self.alarm_screen.showFullScreen()
        
        return True
    
    def _on_alarm_dismissed(self):
        """Handle alarm dismissal."""
        self.alarm_screen = None
        self.wrong_attempts = 0
        
        # Reset wrong code attempts on server
        try:
            import requests
            pc_id = client_config.get_pc_id()
            server_url = client_config.get_server_url()
            requests.post(
                f"{server_url}/api/pcs/{pc_id}/reset-alarm",
                timeout=5,
            )
        except Exception:
            pass
    
    def increment_wrong_attempts(self) -> bool:
        """Increment wrong code attempts. Returns True if alarm should trigger."""
        self.wrong_attempts += 1
        
        if self.wrong_attempts >= self.max_attempts:
            self.wrong_attempts = 0
            return True
        
        return False
    
    def reset_attempts(self):
        """Reset wrong code attempts."""
        self.wrong_attempts = 0
    
    def is_alarm_active(self) -> bool:
        """Check if alarm is currently active."""
        return self.alarm_screen is not None


# Global alarm service instance
alarm_service = AlarmService()
