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
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QFont
from services.session import SessionManager
from services.heartbeat import HeartbeatThread
from services.realtime import RealtimeThread
from services.offline import OfflineManager
from services.config_manager import client_config
from services.security_controller import SecurityController
from services.master_code import MasterCodeValidator
from services.kiosk_guard import should_block_quit_shortcut, should_block_window_close
from ui.session_overlay import SessionOverlay


class LockScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.offline_manager = OfflineManager()
        self.heartbeat_thread = None
        self.realtime_thread = None
        self.session_overlay = None
        self.security = SecurityController(self)
        self.master_code_validator = MasterCodeValidator()
        self.current_pc_id = client_config.get_pc_id()
        self._offline_grace_ticks = 0
        self._production_mode = client_config.is_production_mode()

        self.setup_ui()
        self.setup_timer()
        self._setup_kiosk_watchdog()
        self._wire_security()
        self.start_pc_heartbeat()
        self.start_realtime()

        self._offline_lock_timer = QTimer(self)
        self._offline_lock_timer.setSingleShot(True)
        self._offline_lock_timer.timeout.connect(self._on_offline_lock_timeout)

    def _setup_kiosk_watchdog(self):
        self._kiosk_timer = QTimer(self)
        self._kiosk_timer.timeout.connect(self._enforce_kiosk_state)
        self._kiosk_timer.start(2000)

    def _enforce_kiosk_state(self):
        if not client_config.is_production_mode():
            return
        if self.session_manager.is_active:
            return
        if self.isMinimized() or not self.isVisible() or not self.isFullScreen():
            self.show_lock_ui()

    def _wire_security(self):
        self.security.start()
        self.security.force_lock.connect(self.on_session_expired)
        self.security.force_logout.connect(self._admin_force_logout)
        self.security.refresh_rules.connect(self.security.refresh_filter_rules)
        self.security.extend_session.connect(self._admin_extend_session)

    def setup_ui(self):
        self.setWindowTitle("CyberCafe")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        central_widget = QWidget()
        central_widget.setObjectName("lockScreenCentral")
        central_widget.setStyleSheet(
            "#lockScreenCentral { background-color: #1a1a2e; }"
        )
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("CYBER CAFE")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e94560;")
        main_layout.addWidget(title_label)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.create_code_entry_screen()
        self.create_status_screen()

        self.stack.setCurrentIndex(0)
        self._apply_production_ui()

    def _apply_production_ui(self):
        self._production_mode = client_config.is_production_mode()
        exit_allowed = client_config.is_exit_allowed()

        if exit_allowed:
            self.exit_btn.show()
            self.settings_btn.show()
            self.hint_label.setText("Press Esc to exit  |  Settings to reconfigure")
        elif self._production_mode:
            self.exit_btn.hide()
            self.settings_btn.hide()
            self.hint_label.setText("Enter your access code to start")
        else:
            self.exit_btn.show()
            self.settings_btn.show()
            self.hint_label.setText("Press Esc to exit  |  Settings to reconfigure")

    def create_code_entry_screen(self):
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.enter_code_label = QLabel("Enter Access Code")
        self.enter_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.enter_code_label.setFont(QFont("Arial", 24))
        layout.addWidget(self.enter_code_label)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("XXXX-XXXX-XXXX")
        self.code_input.setMaxLength(20)
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_input.setFont(QFont("Arial", 18))
        self.code_input.returnPressed.connect(self.on_code_submit)
        layout.addWidget(self.code_input)

        submit_btn = QPushButton("START SESSION")
        submit_btn.setMinimumHeight(50)
        submit_btn.clicked.connect(self.on_code_submit)
        layout.addWidget(submit_btn)

        self.code_status_label = QLabel("")
        self.code_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_status_label.setStyleSheet("color: #ff6b6b; background: transparent;")
        layout.addWidget(self.code_status_label)

        self.hint_label = QLabel("Press Esc to exit  |  Settings to reconfigure")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet("color: #95afc0; font-size: 12px; background: transparent;")
        layout.addWidget(self.hint_label)

        bottom_layout = QHBoxLayout()

        self.staff_btn = QPushButton("Staff")
        self.staff_btn.clicked.connect(self.open_staff_login)
        bottom_layout.addWidget(self.staff_btn)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        bottom_layout.addWidget(self.settings_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.exit_btn)

        layout.addLayout(bottom_layout)

        self.stack.addWidget(screen)

    def create_status_screen(self):
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFont(QFont("Arial", 72, QFont.Weight.Bold))
        self.time_label.setStyleSheet("color: #4ecdc4;")
        layout.addWidget(self.time_label)

        self.status_label = QLabel("ACTIVE SESSION")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 24))
        layout.addWidget(self.status_label)

        pc_number = client_config.get("pc_number", self.current_pc_id)
        self.pc_label = QLabel(f"PC #{pc_number}")
        self.pc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pc_label.setFont(QFont("Arial", 16))
        self.pc_label.setStyleSheet("color: #95afc0;")
        layout.addWidget(self.pc_label)

        logout_btn = QPushButton("LOGOUT (Pause Session)")
        logout_btn.setMinimumHeight(50)
        logout_btn.clicked.connect(self.on_logout)
        layout.addWidget(logout_btn)

        self.stack.addWidget(screen)

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def update_time(self):
        if not self.session_manager.is_active:
            return

        self.session_manager.tick(1)
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

        success, message, session_data = self.session_manager.authenticate(
            code, self.current_pc_id
        )

        if success and session_data:
            self.session_manager.apply_session(session_data, code)
            self._offline_grace_ticks = 0
            self._on_session_started()
            self.code_status_label.setText("")
            self.code_input.clear()
            self.enter_session_mode()
        else:
            self.code_status_label.setText(message)
            self.offline_manager.queue_action(
                "code_attempt", {"code": code, "pc_id": self.current_pc_id}
            )

    def _on_session_started(self):
        if self.heartbeat_thread:
            self.heartbeat_thread.set_session_active(True)
            self.heartbeat_thread.set_access_code(self.session_manager.access_code)
        if self.realtime_thread:
            self.realtime_thread.set_session_active(True)
        self.security.on_session_started()

    def _ensure_session_overlay(self):
        if self.session_overlay is None:
            self.session_overlay = SessionOverlay()
            self.session_overlay.logout_requested.connect(self.on_logout)

    def enter_session_mode(self):
        self._ensure_session_overlay()
        remaining = self.session_manager.get_remaining_seconds()
        self.session_overlay.set_time_text(self._format_remaining(remaining))
        self.hide()
        self.session_overlay.show()
        self.session_overlay.raise_()

    def show_lock_ui(self):
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
        self._apply_production_ui()

    def start_realtime(self):
        if self.realtime_thread and self.realtime_thread.isRunning():
            return

        self.realtime_thread = RealtimeThread(self.current_pc_id)
        self.realtime_thread.set_session_active(self.session_manager.is_active)
        self.realtime_thread.command_signal.connect(self.security.handle_commands)
        self.realtime_thread.config_update.connect(self._on_config_update)
        self.realtime_thread.server_offline.connect(self._on_server_offline)
        self.realtime_thread.server_online.connect(self._on_server_online)
        self.realtime_thread.start()

    def _on_server_offline(self):
        if self.heartbeat_thread:
            self.heartbeat_thread.set_ws_offline(True)
        if self.session_manager.is_active:
            self._offline_lock_timer.start(3000)

    def _on_server_online(self):
        self._offline_lock_timer.stop()
        if self.heartbeat_thread:
            self.heartbeat_thread.set_ws_offline(False)
            self.heartbeat_thread.reset_offline_misses()

    def _on_offline_lock_timeout(self):
        if (
            self.session_manager.is_active
            and self.realtime_thread
            and not self.realtime_thread.is_connected
        ):
            self.on_session_expired()

    def start_pc_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.isRunning():
            return

        self.heartbeat_thread = HeartbeatThread(self.current_pc_id)
        self.heartbeat_thread.set_session_active(self.session_manager.is_active)
        if self.session_manager.access_code:
            self.heartbeat_thread.set_access_code(self.session_manager.access_code)

        self.heartbeat_thread.lock_signal.connect(self.on_session_expired)
        self.heartbeat_thread.session_update.connect(self.on_session_heartbeat)
        self.heartbeat_thread.ban_signal.connect(self.on_banned)
        self.heartbeat_thread.config_update.connect(self._on_config_update)
        self.heartbeat_thread.command_signal.connect(self.security.handle_commands)
        self.heartbeat_thread.start()

    def on_session_heartbeat(self, data: dict):
        if not self.session_manager.is_active:
            return

        if not self.session_manager.sync_from_heartbeat(data):
            self.on_session_expired()
            return

        self._offline_grace_ticks = 0
        remaining = self.session_manager.get_remaining_seconds()
        time_text = self._format_remaining(remaining)
        self.time_label.setText(time_text)
        if self.session_overlay and self.session_overlay.isVisible():
            self.session_overlay.set_time_text(time_text)

    def _on_config_update(self, config: dict):
        self.security.apply_server_config(config)
        self._apply_production_ui()

    def on_banned(self):
        QMessageBox.warning(
            self,
            "PC Banned",
            "This PC has been banned. Contact the administrator.",
        )
        self.on_session_expired()

    def on_session_expired(self):
        self._offline_lock_timer.stop()
        self.session_manager.clear_session()
        if self.heartbeat_thread:
            self.heartbeat_thread.set_session_active(False)
        if self.realtime_thread:
            self.realtime_thread.set_session_active(False)
        self.security.on_session_ended()
        self.show_lock_ui()

    def _admin_force_logout(self):
        # Server already paused the session when the admin command was queued.
        self.on_session_expired()

    def _admin_extend_session(self, additional_minutes: float):
        if self.session_manager.is_active:
            self.session_manager.extend_local(additional_minutes * 60)

    def on_logout(self):
        parent = (
            self.session_overlay
            if self.session_overlay and self.session_overlay.isVisible()
            else self
        )
        reply = QMessageBox.question(
            parent,
            "Logout",
            "Are you sure you want to logout? Your session will be paused.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            paused, message = self.session_manager.logout(self.current_pc_id)
            if not paused:
                QMessageBox.warning(parent, "Logout", message)
                return
            self.on_session_expired()

    def open_staff_login(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Staff Access")
        dialog.setMinimumWidth(360)

        layout = QFormLayout(dialog)
        code_input = QLineEdit()
        code_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Master code:", code_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if not dialog.exec():
            return

        success, message, duration = self.master_code_validator.validate(
            code_input.text().strip()
        )
        if not success:
            QMessageBox.warning(self, "Staff Access", message)
            return

        client_config.unlock_staff_maintenance()
        self._apply_production_ui()
        QMessageBox.information(
            self,
            "Staff Access",
            message or "Staff maintenance enabled. Exit and settings are available until restart.",
        )

    def open_settings(self):
        if not client_config.is_exit_allowed():
            QMessageBox.information(
                self,
                "Settings",
                "Settings are disabled. Staff master code required.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        server_input = QLineEdit(client_config.get_server_url())
        layout.addRow("Server URL:", server_input)

        pc_number_input = QLineEdit(
            str(client_config.get("pc_number", client_config.get_pc_id()))
        )
        layout.addRow("PC Number:", pc_number_input)

        branch_input = QLineEdit(str(client_config.get_branch_id()))
        layout.addRow("Branch ID:", branch_input)

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

            if self.heartbeat_thread:
                self.heartbeat_thread.stop()
            self.start_pc_heartbeat()
            if self.realtime_thread:
                self.realtime_thread.stop()
            self.start_realtime()

            QMessageBox.information(self, "Settings", "Settings saved!")

    def keyPressEvent(self, event):
        if should_block_quit_shortcut(event):
            event.accept()
            return
        if (
            event.key() == Qt.Key.Key_Escape
            and not self.session_manager.is_active
            and client_config.is_exit_allowed()
        ):
            self.close()
            return
        if event.key() in [
            Qt.Key.Key_Alt,
            Qt.Key.Key_F4,
            Qt.Key.Key_Control,
            Qt.Key.Key_Delete,
        ]:
            event.accept()
            return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        if (
            event.type() == QEvent.Type.WindowStateChange
            and client_config.is_production_mode()
            and not self.session_manager.is_active
        ):
            if self.isMinimized() or not self.isFullScreen():
                QTimer.singleShot(0, self.show_lock_ui)
        super().changeEvent(event)

    def closeEvent(self, event):
        if should_block_window_close():
            event.ignore()
            self.show_lock_ui()
            return
        if not self.session_manager.is_active:
            self._offline_lock_timer.stop()
            self.security.stop()
            if self.realtime_thread:
                self.realtime_thread.stop()
            event.accept()
        else:
            event.ignore()
