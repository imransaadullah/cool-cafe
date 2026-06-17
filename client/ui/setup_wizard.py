"""
Setup Wizard
First-time configuration wizard for the client
"""

import sys
import socket
import uuid
import requests
import secrets
import string
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QStackedWidget,
    QCheckBox, QSpinBox, QColorDialog, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from services.config_manager import client_config
from services.kiosk_guard import should_block_window_close


def get_local_ip():
    """Get the local IP address on the LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_mac_address():
    """Get the MAC address of this machine."""
    try:
        node = uuid.getnode()
        return ":".join(f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8))
    except Exception:
        return None


def register_pc_with_server(server_url, name, pc_number, branch_id):
    """
    Register this PC with the server and return the database PC id.
    Raises requests.RequestException or ValueError on failure.
    """
    response = requests.post(
        f"{server_url.rstrip('/')}/api/pcs/register",
        json={
            "name": name,
            "pc_number": pc_number,
            "branch_id": branch_id,
            "ip_address": get_local_ip(),
            "mac_address": get_mac_address(),
        },
        timeout=10,
    )
    if response.status_code != 200:
        detail = response.json().get("detail", response.text)
        raise ValueError(f"Server error: {detail}")
    return response.json()["id"]


class SetupWizard(QMainWindow):
    """Setup wizard for first-time configuration."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CyberCafe Client Setup")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(Qt.WindowType.Window)
        
        # Generated security data
        self.static_code = None
        self.recovery_combo = None
        self.registered_pc_id = None
        
        # Callback to launch lock screen after setup
        self.lock_screen_callback = None
        self._allow_close = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the wizard UI."""
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("setupWizardCentral")
        central_widget.setStyleSheet(
            "#setupWizardCentral { background-color: #1a1a2e; }"
        )
        self.setCentralWidget(central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("CyberCafe Client Setup")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.main_layout.addWidget(title)
        
        # Stacked widget for steps
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        
        # Create steps
        self.create_step1()
        self.create_step2()
        self.create_step3()
        self.create_step4()
        self.create_step5()
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.prev_step)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.next_step)
        nav_layout.addWidget(self.next_btn)
        
        self.main_layout.addLayout(nav_layout)
        
        # Show first step
        self.stack.setCurrentIndex(0)
    
    def create_step1(self):
        """Step 1: Server Connection."""
        step = QWidget()
        layout = QVBoxLayout(step)
        
        # Step label
        step_label = QLabel("Step 1: Server Connection")
        step_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(step_label)
        
        # Server URL (must be the cafe server's IP, not this PC's IP)
        layout.addWidget(QLabel("Server URL:"))
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://192.168.1.100:8000")
        layout.addWidget(self.server_url_input)

        hint_label = QLabel(
            "Enter the IP address of the cafe server PC (not this computer)."
        )
        hint_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(hint_label)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_btn)
        
        # Status label
        self.connection_status = QLabel("")
        layout.addWidget(self.connection_status)
        
        layout.addStretch()
        self.stack.addWidget(step)
    
    def create_step2(self):
        """Step 2: PC Identification."""
        step = QWidget()
        layout = QVBoxLayout(step)
        
        # Step label
        step_label = QLabel("Step 2: PC Identification")
        step_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(step_label)
        
        # PC Name
        layout.addWidget(QLabel("PC Name:"))
        self.pc_name_input = QLineEdit()
        self.pc_name_input.setPlaceholderText("e.g., PC-01")
        layout.addWidget(self.pc_name_input)
        
        # PC Number (display number; server assigns the database ID)
        layout.addWidget(QLabel("PC Number:"))
        self.pc_number_input = QSpinBox()
        self.pc_number_input.setRange(1, 1000)
        self.pc_number_input.setValue(1)
        layout.addWidget(self.pc_number_input)

        pc_hint = QLabel("The number shown on this station (e.g. PC #1, PC #2).")
        pc_hint.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(pc_hint)
        
        # Branch ID
        layout.addWidget(QLabel("Branch ID:"))
        self.branch_id_input = QSpinBox()
        self.branch_id_input.setRange(1, 100)
        self.branch_id_input.setValue(1)
        layout.addWidget(self.branch_id_input)
        
        layout.addStretch()
        self.stack.addWidget(step)
    
    def create_step3(self):
        """Step 3: Security Setup."""
        step = QWidget()
        layout = QVBoxLayout(step)
        
        # Step label
        step_label = QLabel("Step 3: Security Setup")
        step_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(step_label)
        
        # Generate codes button
        self.generate_btn = QPushButton("Generate Security Codes")
        self.generate_btn.clicked.connect(self.generate_codes)
        layout.addWidget(self.generate_btn)
        
        # Static code display
        layout.addWidget(QLabel("Static Master Code:"))
        self.static_code_label = QLabel("Click 'Generate' to create")
        self.static_code_label.setStyleSheet("font-family: monospace; font-size: 14px;")
        layout.addWidget(self.static_code_label)
        
        # Recovery combo display
        layout.addWidget(QLabel("Recovery Key Combo:"))
        self.recovery_combo_label = QLabel("Click 'Generate' to create")
        self.recovery_combo_label.setStyleSheet("font-family: monospace; font-size: 14px;")
        layout.addWidget(self.recovery_combo_label)
        
        # Warning
        warning = QLabel("⚠ Save these codes - they cannot be recovered!")
        warning.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(warning)
        
        layout.addStretch()
        self.stack.addWidget(step)
    
    def create_step4(self):
        """Step 4: Startup Options."""
        step = QWidget()
        layout = QVBoxLayout(step)
        
        # Step label
        step_label = QLabel("Step 4: Startup Options")
        step_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(step_label)
        
        # Auto-start on boot
        self.auto_start_checkbox = QCheckBox("Auto-start on boot")
        self.auto_start_checkbox.setChecked(True)
        layout.addWidget(self.auto_start_checkbox)
        
        # Run as Windows Service
        self.service_checkbox = QCheckBox("Run as Windows Service")
        self.service_checkbox.setChecked(False)
        layout.addWidget(self.service_checkbox)
        
        # Heartbeat interval
        layout.addWidget(QLabel("Heartbeat interval (seconds):"))
        self.heartbeat_input = QSpinBox()
        self.heartbeat_input.setRange(10, 300)
        self.heartbeat_input.setValue(30)
        layout.addWidget(self.heartbeat_input)
        
        # Alarm enabled
        self.alarm_checkbox = QCheckBox("Enable alarm on security breach")
        self.alarm_checkbox.setChecked(True)
        layout.addWidget(self.alarm_checkbox)
        
        # Alarm color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Alarm color:"))
        self.alarm_color_input = QLineEdit("#FF0000")
        self.alarm_color_input.setMaximumWidth(100)
        color_layout.addWidget(self.alarm_color_input)
        
        self.color_btn = QPushButton("Choose")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        
        layout.addLayout(color_layout)
        
        layout.addStretch()
        self.stack.addWidget(step)
    
    def create_step5(self):
        """Step 5: Complete."""
        step = QWidget()
        layout = QVBoxLayout(step)
        
        # Step label
        step_label = QLabel("Step 5: Complete")
        step_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(step_label)
        
        # Success message
        success_label = QLabel("✅ Setup Complete!")
        success_label.setFont(QFont("Arial", 18))
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(success_label)
        
        # Summary
        summary = QLabel("Configuration saved. Client will start in 5 seconds...")
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(summary)
        
        # Start now button
        self.start_btn = QPushButton("Start Now")
        self.start_btn.clicked.connect(self.start_client)
        layout.addWidget(self.start_btn)
        
        layout.addStretch()
        self.stack.addWidget(step)
    
    def test_connection(self):
        """Test server connection."""
        server_url = self.server_url_input.text().strip()
        
        try:
            response = requests.get(f"{server_url}/api/health", timeout=10)
            if response.status_code == 200:
                self.connection_status.setText("✅ Connected to server")
                self.connection_status.setStyleSheet("color: green;")
            else:
                self.connection_status.setText(f"❌ Server error: {response.status_code}")
                self.connection_status.setStyleSheet("color: red;")
        except requests.exceptions.RequestException as e:
            self.connection_status.setText(f"❌ Connection failed: {str(e)}")
            self.connection_status.setStyleSheet("color: red;")
    
    def generate_codes(self):
        """Generate static code and recovery combo."""
        # Generate static master code (format: XXXX-XXXX-XXXX)
        chars = string.ascii_uppercase + string.digits
        parts = []
        for _ in range(3):
            part = ''.join(secrets.choice(chars) for _ in range(4))
            parts.append(part)
        self.static_code = '-'.join(parts)
        
        # Generate recovery combo (3 random keys)
        keys_pool = (
            [f"F{i}" for i in range(1, 13)] +
            list(string.ascii_uppercase) +
            list(string.digits)
        )
        self.recovery_combo = [secrets.choice(keys_pool) for _ in range(3)]
        
        # Update labels
        self.static_code_label.setText(self.static_code)
        self.recovery_combo_label.setText("Alt + " + " + ".join(self.recovery_combo))
    
    def choose_color(self):
        """Open color chooser dialog."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.alarm_color_input.setText(color.name())
    
    def next_step(self):
        """Go to next step."""
        current = self.stack.currentIndex()
        
        # Validate current step
        if current == 0:
            if not self.server_url_input.text().strip():
                QMessageBox.warning(self, "Error", "Please enter server URL")
                return
        elif current == 1:
            if not self.pc_name_input.text().strip():
                QMessageBox.warning(self, "Error", "Please enter PC name")
                return
            server_url = self.server_url_input.text().strip()
            try:
                pc_id = register_pc_with_server(
                    server_url,
                    self.pc_name_input.text().strip(),
                    self.pc_number_input.value(),
                    self.branch_id_input.value(),
                )
                self.registered_pc_id = pc_id
            except requests.exceptions.RequestException as e:
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    f"Could not register PC with server.\n\n{e}\n\n"
                    "Check the server URL and make sure the server is running.",
                )
                return
            except ValueError as e:
                QMessageBox.warning(self, "Registration Error", str(e))
                return
        elif current == 2:
            if not self.static_code or not self.recovery_combo:
                QMessageBox.warning(self, "Error", "Please generate security codes")
                return
        
        # Save settings
        if current == 0:
            client_config.set("server_url", self.server_url_input.text().strip())
        elif current == 1:
            client_config.set("pc_name", self.pc_name_input.text().strip())
            client_config.set("pc_number", self.pc_number_input.value())
            client_config.set("pc_id", self.registered_pc_id)
            client_config.set("branch_id", self.branch_id_input.value())
        elif current == 2:
            client_config.set("security.static_master_code", self.static_code)
            client_config.set("security.recovery_combo", "+".join(self.recovery_combo))
            server_url = self.server_url_input.text().strip()
            pc_id = client_config.get("pc_id")
            try:
                requests.post(
                    f"{server_url.rstrip('/')}/api/pcs/{pc_id}/register-static-code",
                    json={
                        "static_master_code": self.static_code,
                        "recovery_key_combo": "+".join(self.recovery_combo),
                    },
                    timeout=10,
                )
            except requests.exceptions.RequestException:
                pass
        elif current == 3:
            client_config.set("security.auto_start_enabled", self.auto_start_checkbox.isChecked())
            client_config.set("security.run_as_service", self.service_checkbox.isChecked())
            client_config.set("heartbeat_interval", self.heartbeat_input.value())
            client_config.set("security.alarm_enabled", self.alarm_checkbox.isChecked())
            client_config.set("security.alarm_color", self.alarm_color_input.text())
            from services.watchdog_install import apply_security_options
            apply_security_options(
                run_as_service=self.service_checkbox.isChecked(),
                auto_start_enabled=self.auto_start_checkbox.isChecked(),
            )
        
        # Go to next step
        if current < 4:
            self.stack.setCurrentIndex(current + 1)
            self.prev_btn.setEnabled(True)
            
            if current == 3:
                self.next_btn.setEnabled(False)
                # Auto-start client after 5 seconds
                QTimer.singleShot(5000, self.start_client)
    
    def prev_step(self):
        """Go to previous step."""
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.next_btn.setEnabled(True)
            
            if current == 1:
                self.prev_btn.setEnabled(False)
    
    def start_client(self):
        """Start the main client."""
        client_config.set("configured", True)
        self._allow_close = True
        self.close()
        if self.lock_screen_callback:
            self.lock_screen_callback()

    def closeEvent(self, event):
        if not self._allow_close and should_block_window_close():
            event.ignore()
            return
        super().closeEvent(event)


def check_first_run() -> bool:
    """Check if this is first run (setup wizard not completed)."""
    return not client_config.is_configured()
