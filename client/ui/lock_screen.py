from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QStackedWidget,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from services.session import SessionManager
from services.heartbeat import HeartbeatThread
from services.offline import OfflineManager
from services.config_manager import client_config


class LockScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.offline_manager = OfflineManager()
        self.heartbeat_thread = None
        self.current_pc_id = client_config.get_pc_id()
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        self.setWindowTitle("CyberCafe")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        title_label = QLabel("CYBER CAFE")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e94560;")
        main_layout.addWidget(title_label)
        
        # Stacked widget for different screens
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # Create screens
        self.create_code_entry_screen()
        self.create_status_screen()
        
        # Show code entry screen by default
        self.stack.setCurrentIndex(0)
    
    def create_code_entry_screen(self):
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Code entry label
        enter_code_label = QLabel("Enter Access Code")
        enter_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        enter_code_label.setFont(QFont("Arial", 24))
        layout.addWidget(enter_code_label)
        
        # Code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("XXXX-XXXX-XXXX")
        self.code_input.setMaxLength(20)
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_input.setFont(QFont("Arial", 18))
        self.code_input.returnPressed.connect(self.on_code_submit)
        layout.addWidget(self.code_input)
        
        # Submit button
        submit_btn = QPushButton("START SESSION")
        submit_btn.setMinimumHeight(50)
        submit_btn.clicked.connect(self.on_code_submit)
        layout.addWidget(submit_btn)
        
        # Status label
        self.code_status_label = QLabel("")
        self.code_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_status_label.setStyleSheet("color: #ff6b6b;")
        layout.addWidget(self.code_status_label)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        bottom_layout.addWidget(settings_btn)
        
        # Exit button (only visible when no session)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.exit_btn)
        
        layout.addLayout(bottom_layout)
        
        self.stack.addWidget(screen)
    
    def create_status_screen(self):
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Time remaining label
        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(QFont("Arial", 72, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #4ecdc4;")
        layout.addWidget(self.time_label)
        
        # Status label
        self.status_label = QLabel("ACTIVE SESSION")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 24))
        layout.addWidget(self.status_label)
        
        # PC info
        self.pc_label = QLabel(f"PC #{self.current_pc_id}")
        self.pc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pc_label.setFont(QFont("Arial", 16))
        self.pc_label.setStyleSheet("color: #95afc0;")
        layout.addWidget(self.pc_label)
        
        # Logout button
        logout_btn = QPushButton("LOGOUT (Pause Session)")
        logout_btn.setMinimumHeight(50)
        logout_btn.clicked.connect(self.on_logout)
        layout.addWidget(logout_btn)
        
        self.stack.addWidget(screen)
    
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second
    
    def update_time(self):
        if self.session_manager.is_active:
            remaining = self.session_manager.get_remaining_seconds()
            if remaining <= 0:
                self.lock_screen()
                return
            
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def on_code_submit(self):
        code = self.code_input.text().strip()
        if not code:
            self.code_status_label.setText("Please enter a code")
            return
        
        self.code_status_label.setText("Validating code...")
        
        # Try to validate with server
        success, message, session_data = self.session_manager.redeem_code(
            code, self.current_pc_id
        )
        
        if success:
            self.session_manager.start_session(session_data)
            self.start_heartbeat()
            self.stack.setCurrentIndex(1)
            self.code_status_label.setText("")
        else:
            self.code_status_label.setText(message)
            # Store failed attempt for offline queue
            self.offline_manager.queue_action(
                "code_attempt", {"code": code, "pc_id": self.current_pc_id}
            )
    
    def start_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.isRunning():
            self.heartbeat_thread.stop()
        
        self.heartbeat_thread = HeartbeatThread(self.current_pc_id)
        self.heartbeat_thread.lock_signal.connect(self.lock_screen)
        self.heartbeat_thread.start()
    
    def lock_screen(self):
        self.session_manager.end_session()
        if self.heartbeat_thread:
            self.heartbeat_thread.stop()
        self.stack.setCurrentIndex(0)
        self.code_input.clear()
        self.time_label.setText("00:00:00")
    
    def on_logout(self):
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout? Your session will be paused.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.session_manager.pause_session()
            self.lock_screen()
    
    def open_settings(self):
        """Open settings dialog to configure server URL."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(400)
        
        layout = QFormLayout(dialog)
        
        # Server URL
        server_input = QLineEdit(client_config.get_server_url())
        layout.addRow("Server URL:", server_input)
        
        # PC ID
        pc_input = QLineEdit(str(client_config.get_pc_id()))
        layout.addRow("PC ID:", pc_input)
        
        # Branch ID
        branch_input = QLineEdit(str(client_config.get_branch_id()))
        layout.addRow("Branch ID:", branch_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec():
            # Save settings
            client_config.set("server_url", server_input.text())
            client_config.set("pc_id", int(pc_input.text()))
            client_config.set("branch_id", int(branch_input.text()))
            
            # Update session manager
            self.session_manager.server_url = server_input.text()
            self.current_pc_id = int(pc_input.text())
            
            QMessageBox.information(self, "Settings", "Settings saved!")
    
    def keyPressEvent(self, event):
        # Allow Escape to exit when no active session
        if event.key() == Qt.Key.Key_Escape and not self.session_manager.is_active:
            self.close()
            return
        # Disable Alt+F4 and other system keys
        if event.key() in [
            Qt.Key.Key_Alt,
            Qt.Key.Key_F4,
            Qt.Key.Key_Control,
            Qt.Key.Key_Delete,
        ]:
            return
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        # Allow closing when no active session
        if not self.session_manager.is_active:
            event.accept()
        else:
            event.ignore()
