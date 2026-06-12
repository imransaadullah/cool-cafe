"""Small always-on-top timer shown while a session is active."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class SessionOverlay(QWidget):
    """Floating session timer — lets the user access the desktop."""

    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SessionOverlay")
        self.setWindowTitle("CyberCafe Session")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(260, 90)
        self.setStyleSheet(
            "#SessionOverlay { background-color: rgba(26, 26, 46, 220); border-radius: 8px; }"
            "QLabel { color: #ffffff; background: transparent; }"
            "QPushButton { background-color: #e94560; color: white; border: none;"
            " padding: 6px 12px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #c73e54; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        header = QLabel("SESSION ACTIVE")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #95afc0; font-size: 11px;")
        layout.addWidget(header)

        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #4ecdc4;")
        layout.addWidget(self.time_label)

        btn_row = QHBoxLayout()
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout_requested.emit)
        btn_row.addWidget(logout_btn)
        layout.addLayout(btn_row)

    def set_time_text(self, text: str):
        self.time_label.setText(text)

    def position_corner(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        margin = 16
        self.move(
            geo.right() - self.width() - margin,
            geo.bottom() - self.height() - margin,
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.position_corner()
