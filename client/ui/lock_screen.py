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
from ui.session_overlay import SessionOverlay


class LockScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.offline_manager = OfflineManager()
        self.heartbeat_thread = None
        self.session_overlay = None
        self.pending_resume = None
        self.current_pc_id = client_config.get_pc_id()
        
        self.setup_ui()
        self.setup_timer()
        self.restore_active_session()
        self.refresh_resume_status()
    
    def setup_ui(self):
        self.setWindowTitle("CyberCafe")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("lockScreenCentral")
        central_widget.setStyleSheet(
            "#lockScreenCentral { background-color: #1a1a2e; }"
        )
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
        self.enter_code_label = QLabel("Enter Access Code")
        self.enter_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.enter_code_label.setFont(QFont("Arial", 24))
        layout.addWidget(self.enter_code_label)
        
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

        self.resume_btn = QPushButton("RESUME SESSION")
        self.resume_btn.setMinimumHeight(50)
        self.resume_btn.clicked.connect(self.on_resume_session)
        self.resume_btn.setVisible(False)
        layout.addWidget(self.resume_btn)

        self.resume_info_label = QLabel("")
        self.resume_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resume_info_label.setStyleSheet("color: #4ecdc4; font-size: 13px; background: transparent;")
        self.resume_info_label.setVisible(False)
        layout.addWidget(self.resume_info_label)
        
        # Status label
        self.code_status_label = QLabel("")
        self.code_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_status_label.setStyleSheet("color: #ff6b6b; background: transparent;")
        layout.addWidget(self.code_status_label)

        # Hint for exiting when locked
        hint_label = QLabel("Press Esc to exit  |  Settings to reconfigure")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet("color: #95afc0; font-size: 12px; background: transparent;")
        layout.addWidget(hint_label)
        
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
        pc_number = client_config.get("pc_number", self.current_pc_id)
        self.pc_label = QLabel(f"PC #{pc_number}")
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
                self.on_session_expired()
                return

            time_text = self._format_remaining(remaining)
            self.time_label.setText(time_text)
            if self.session_overlay and self.session_overlay.isVisible():
                self.session_overlay.set_time_text(time_text)

    def _format_remaining(self, remaining: float) -> str:
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        seconds = int(remaining % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
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
            self.code_status_label.setText("")
            self.enter_session_mode()
        else:
            if session_data and session_data.get("action") == "resume":
                self.refresh_resume_status()
                self.on_resume_session()
                return
            self.code_status_label.setText(message)
            if "resume" in (message or "").lower():
                self.refresh_resume_status()
            self.offline_manager.queue_action(
                "code_attempt", {"code": code, "pc_id": self.current_pc_id}
            )

    def _complete_resume(self, session_data: dict):
        self.session_manager.start_session(session_data)
        self.start_heartbeat()
        self.code_status_label.setText("")
        self.code_input.clear()
        self.enter_session_mode()

    def on_resume_session(self):
        self.code_status_label.setText("Resuming session...")
        success, message, session_data = self.session_manager.resume_for_pc(
            self.current_pc_id
        )

        if not success and self.pending_resume and self.pending_resume.get("session_id"):
            success, message, session_data = (
                self.session_manager.resume_paused_session(
                    self.pending_resume["session_id"]
                )
            )

        if success and session_data:
            self._complete_resume(session_data)
        else:
            self.code_status_label.setText(message or "Cannot resume session")
            self.refresh_resume_status()

    def refresh_resume_status(self):
        """Update resume button based on server paused session state."""
        info = self.session_manager.get_resume_info(self.current_pc_id)
        self.pending_resume = info

        if info and info.get("can_resume"):
            remaining = info.get("remaining_seconds") or 0
            logins_left = info.get("resumes_remaining", 0)
            max_res = info.get("max_resumes", 0)
            self.enter_code_label.setText("Session Paused")
            self.code_input.setPlaceholderText("New code only (optional)")
            self.resume_btn.setVisible(True)
            self.resume_btn.setEnabled(True)
            self.resume_btn.setText(
                f"RESUME SESSION ({self._format_remaining(remaining)} left)"
            )
            self.resume_info_label.setText(
                f"No code needed — {logins_left} of {max_res} re-login(s) left"
            )
            self.resume_info_label.setStyleSheet(
                "color: #4ecdc4; font-size: 13px; background: transparent;"
            )
            self.resume_info_label.setVisible(True)
        elif info and info.get("session_id"):
            self.enter_code_label.setText("Session Paused")
            self.code_input.setPlaceholderText("New code only (optional)")
            self.resume_btn.setVisible(True)
            self.resume_btn.setEnabled(False)
            self.resume_btn.setText("RESUME SESSION")
            self.resume_info_label.setText(
                info.get("message", "Cannot resume this session")
            )
            self.resume_info_label.setStyleSheet(
                "color: #ff6b6b; font-size: 13px; background: transparent;"
            )
            self.resume_info_label.setVisible(True)
        else:
            self.enter_code_label.setText("Enter Access Code")
            self.code_input.setPlaceholderText("XXXX-XXXX-XXXX")
            self.resume_btn.setVisible(False)
            self.resume_info_label.setVisible(False)
    
    def restore_active_session(self):
        """Resume UI and heartbeat if a valid session was cached."""
        if self.session_manager.is_active:
            self.start_heartbeat()
            self.enter_session_mode()

    def _ensure_session_overlay(self):
        if self.session_overlay is None:
            self.session_overlay = SessionOverlay()
            self.session_overlay.logout_requested.connect(self.on_logout)

    def enter_session_mode(self):
        """Hide the lock screen and release the desktop for the user."""
        self._ensure_session_overlay()
        remaining = self.session_manager.get_remaining_seconds()
        self.session_overlay.set_time_text(self._format_remaining(remaining))
        self.hide()
        self.session_overlay.show()
        self.session_overlay.raise_()

    def show_lock_ui(self):
        """Show the fullscreen code-entry screen."""
        if self.session_overlay:
            self.session_overlay.hide()
        self.stack.setCurrentIndex(0)
        self.code_input.clear()
        self.code_status_label.setText("")
        self.time_label.setText("00:00:00")
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.code_input.setFocus()
        self.refresh_resume_status()

    def start_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.isRunning():
            self.heartbeat_thread.stop()

        self.heartbeat_thread = HeartbeatThread(self.current_pc_id)
        self.heartbeat_thread.set_session_active(self.session_manager.is_active)
        self.heartbeat_thread.lock_signal.connect(self.on_session_expired)
        self.heartbeat_thread.ban_signal.connect(self.on_banned)
        self.heartbeat_thread.start()

    def on_banned(self):
        QMessageBox.warning(
            self,
            "PC Banned",
            "This PC has been banned. Contact the administrator.",
        )
        self.on_session_expired()

    def on_session_expired(self):
        """Session time ran out — end session and return to lock screen."""
        self.session_manager.end_session()
        self._stop_heartbeat()
        self.show_lock_ui()

    def _stop_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.isRunning():
            self.heartbeat_thread.stop()
            self.heartbeat_thread = None

    def on_logout(self):
        parent = self.session_overlay if self.session_overlay and self.session_overlay.isVisible() else self
        reply = QMessageBox.question(
            parent,
            "Logout",
            "Are you sure you want to logout? Your session will be paused.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            paused, message = self.session_manager.pause_session()
            if not paused:
                QMessageBox.warning(parent, "Logout", message)
                return
            self._stop_heartbeat()
            self.show_lock_ui()
    
    def open_settings(self):
        """Open settings dialog to configure server URL."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(400)
        
        layout = QFormLayout(dialog)
        
        # Server URL
        server_input = QLineEdit(client_config.get_server_url())
        layout.addRow("Server URL:", server_input)
        
        # PC Number
        pc_number_input = QLineEdit(str(client_config.get("pc_number", client_config.get_pc_id())))
        layout.addRow("PC Number:", pc_number_input)
        
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
            server_url = server_input.text().strip()
            pc_number = int(pc_number_input.text())
            branch_id = int(branch_input.text())

            try:
                from ui.setup_wizard import register_pc_with_server
                pc_id = register_pc_with_server(
                    server_url,
                    client_config.get("pc_name", f"PC-{pc_number}"),
                    pc_number,
                    branch_id,
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Settings Error",
                    f"Could not register with server: {e}",
                )
                return

            client_config.set("server_url", server_url)
            client_config.set("pc_number", pc_number)
            client_config.set("pc_id", pc_id)
            client_config.set("branch_id", branch_id)
            client_config.set("configured", True)

            self.session_manager.server_url = server_url
            self.current_pc_id = pc_id
            self.pc_label.setText(f"PC #{pc_number}")

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
