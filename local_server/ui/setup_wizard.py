"""
First-run installation wizard for CyberCafe Server.
Collects database, branch, admin, and network settings then applies setup.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

ROOT = Path(__file__).resolve().parents[2]
LOCAL_SERVER = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LOCAL_SERVER) not in sys.path:
    sys.path.insert(0, str(LOCAL_SERVER))

from services.setup_runner import SetupConfig, run_full_setup, test_database_connection


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class SetupWorker(QThread):
    finished = pyqtSignal(bool, str)
    log_line = pyqtSignal(str)

    def __init__(self, config: SetupConfig):
        super().__init__()
        self.config = config

    def run(self):
        ok, msg = run_full_setup(self.config, log=self.log_line.emit)
        self.finished.emit(ok, msg)


class ServerSetupWizard(QMainWindow):
    """Multi-step installer wizard shown on first launch."""

    def __init__(self, on_complete=None):
        super().__init__()
        self.on_complete = on_complete
        self._allow_close = False
        self.setWindowTitle("CyberCafe Server — Installation Setup")
        self.setMinimumSize(640, 560)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("serverSetupCentral")
        central.setStyleSheet("#serverSetupCentral { background-color: #1a1a2e; color: #fff; }")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("CyberCafe Server Setup")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Configure your café server in a few steps")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #aaa; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self._create_welcome_step()
        self._create_database_step()
        self._create_cafe_step()
        self._create_admin_step()
        self._create_network_step()
        self._create_install_step()
        self._create_done_step()

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("Back")
        self.prev_btn.clicked.connect(self._prev_step)
        self.prev_btn.setEnabled(False)
        nav.addWidget(self.prev_btn)

        nav.addStretch()

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._next_step)
        self.next_btn.setStyleSheet("background:#e94560;font-weight:bold;padding:8px 20px;")
        nav.addWidget(self.next_btn)

        layout.addLayout(nav)

    def _form_group(self, title: str) -> tuple[QWidget, QFormLayout]:
        box = QGroupBox(title)
        box.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 12px; }")
        form = QFormLayout(box)
        return box, form

    def _create_welcome_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        text = QLabel(
            "This wizard will:\n\n"
            "• Connect to your PostgreSQL database\n"
            "• Create your café branch\n"
            "• Create the administrator login\n"
            "• Configure the server and dashboard\n\n"
            "Make sure PostgreSQL is installed and running before you continue."
        )
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 14px; line-height: 1.5;")
        lay.addWidget(text)
        lay.addStretch()
        self.stack.addWidget(w)

    def _create_database_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box, form = self._form_group("PostgreSQL Database")

        self.db_host = QLineEdit("localhost")
        self.db_port = QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(5432)
        self.db_user = QLineEdit("postgres")
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_password.setPlaceholderText("PostgreSQL password")
        self.db_name = QLineEdit("cybercafe")

        form.addRow("Host:", self.db_host)
        form.addRow("Port:", self.db_port)
        form.addRow("Username:", self.db_user)
        form.addRow("Password:", self.db_password)
        form.addRow("Database name:", self.db_name)

        lay.addWidget(box)

        test_row = QHBoxLayout()
        self.db_status = QLabel("")
        self.db_status.setStyleSheet("color: #aaa;")
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_database)
        test_row.addWidget(test_btn)
        test_row.addWidget(self.db_status)
        test_row.addStretch()
        lay.addLayout(test_row)
        lay.addStretch()
        self.stack.addWidget(w)

    def _create_cafe_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box, form = self._form_group("Café / Branch")

        self.cafe_name = QLineEdit("My Cyber Café")
        self.branch_name = QLineEdit("Main Branch")
        self.branch_address = QLineEdit()
        self.branch_address.setPlaceholderText("Optional street address")
        self.branch_phone = QLineEdit()
        self.branch_phone.setPlaceholderText("Optional phone number")

        form.addRow("Café name:", self.cafe_name)
        form.addRow("Branch name:", self.branch_name)
        form.addRow("Address:", self.branch_address)
        form.addRow("Phone:", self.branch_phone)

        lay.addWidget(box)
        lay.addStretch()
        self.stack.addWidget(w)

    def _create_admin_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box, form = self._form_group("Administrator Account")

        self.admin_user = QLineEdit("admin")
        self.admin_pass = QLineEdit()
        self.admin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_pass.setPlaceholderText("Choose a strong password")
        self.admin_pass_confirm = QLineEdit()
        self.admin_pass_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_email = QLineEdit()
        self.admin_email.setPlaceholderText("optional@email.com")

        form.addRow("Username:", self.admin_user)
        form.addRow("Password:", self.admin_pass)
        form.addRow("Confirm password:", self.admin_pass_confirm)
        form.addRow("Email:", self.admin_email)

        lay.addWidget(box)
        lay.addStretch()
        self.stack.addWidget(w)

    def _create_network_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box, form = self._form_group("Network & Startup")

        self.server_port = QSpinBox()
        self.server_port.setRange(1024, 65535)
        self.server_port.setValue(8000)

        lan_ip = get_lan_ip()
        self.client_url_label = QLabel(
            f"Clients will connect to: http://{lan_ip}:{self.server_port.value()}"
        )
        self.client_url_label.setWordWrap(True)
        self.client_url_label.setStyleSheet("color: #7fdbca; font-family: monospace;")
        self.server_port.valueChanged.connect(self._update_client_url)

        self.auto_start_cb = QCheckBox("Start services automatically when the app opens")
        self.auto_start_cb.setChecked(True)
        self.open_browser_cb = QCheckBox("Open dashboard in browser when services start")
        self.open_browser_cb.setChecked(True)

        form.addRow("Server port:", self.server_port)
        form.addRow("LAN URL for PCs:", self.client_url_label)
        lay.addWidget(box)
        lay.addWidget(self.auto_start_cb)
        lay.addWidget(self.open_browser_cb)
        lay.addStretch()
        self.stack.addWidget(w)

    def _create_install_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Installing… this may take a minute."))
        self.install_log = QTextEdit()
        self.install_log.setReadOnly(True)
        self.install_log.setStyleSheet(
            "background:#0f0f1a;color:#ccc;font-family:Consolas;font-size:12px;"
        )
        lay.addWidget(self.install_log)
        self.stack.addWidget(w)

    def _create_done_step(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.done_label = QLabel("Setup complete!")
        self.done_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.done_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.done_label.setStyleSheet("color: #4caf50;")
        lay.addWidget(self.done_label)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.summary_label)

        finish_btn = QPushButton("Open Server Manager")
        finish_btn.setStyleSheet("background:#4caf50;font-weight:bold;padding:12px;")
        finish_btn.clicked.connect(self._finish)
        lay.addWidget(finish_btn)
        lay.addStretch()
        self.stack.addWidget(w)

    def _update_client_url(self):
        lan_ip = get_lan_ip()
        port = self.server_port.value()
        self.client_url_label.setText(f"Clients will connect to: http://{lan_ip}:{port}")

    def _build_config(self) -> SetupConfig:
        return SetupConfig(
            cafe_name=self.cafe_name.text().strip() or "My Cyber Café",
            branch_name=self.branch_name.text().strip() or "Main Branch",
            branch_address=self.branch_address.text().strip(),
            branch_phone=self.branch_phone.text().strip(),
            db_host=self.db_host.text().strip() or "localhost",
            db_port=self.db_port.value(),
            db_user=self.db_user.text().strip() or "postgres",
            db_password=self.db_password.text(),
            db_name=self.db_name.text().strip() or "cybercafe",
            admin_username=self.admin_user.text().strip() or "admin",
            admin_password=self.admin_pass.text(),
            admin_email=self.admin_email.text().strip(),
            server_port=self.server_port.value(),
            auto_start=self.auto_start_cb.isChecked(),
            open_browser=self.open_browser_cb.isChecked(),
        )

    def _test_database(self):
        if not self.db_password.text():
            self.db_status.setText("Enter database password")
            self.db_status.setStyleSheet("color: #e94560;")
            return
        self.db_status.setText("Testing…")
        self.db_status.setStyleSheet("color: #aaa;")
        ok, msg = test_database_connection(self._build_config())
        if ok:
            self.db_status.setText(msg)
            self.db_status.setStyleSheet("color: #4caf50;")
        else:
            self.db_status.setText(msg[:200])
            self.db_status.setStyleSheet("color: #e94560;")

    def _validate_step(self, index: int) -> bool:
        if index == 1:
            if not self.db_password.text():
                QMessageBox.warning(self, "Database", "Please enter the PostgreSQL password.")
                return False
            ok, msg = test_database_connection(self._build_config())
            if not ok:
                QMessageBox.warning(self, "Database", f"Could not connect:\n\n{msg}")
                return False
        elif index == 2:
            if not self.cafe_name.text().strip() or not self.branch_name.text().strip():
                QMessageBox.warning(self, "Café", "Please enter café and branch names.")
                return False
        elif index == 3:
            if len(self.admin_pass.text()) < 6:
                QMessageBox.warning(self, "Admin", "Password must be at least 6 characters.")
                return False
            if self.admin_pass.text() != self.admin_pass_confirm.text():
                QMessageBox.warning(self, "Admin", "Passwords do not match.")
                return False
        return True

    def _prev_step(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self.prev_btn.setEnabled(idx - 1 > 0)
            self.next_btn.setEnabled(True)
            self.next_btn.setText("Install" if idx - 1 == 4 else "Next")

    def _next_step(self):
        idx = self.stack.currentIndex()
        if idx < 4:
            if not self._validate_step(idx):
                return
            next_idx = idx + 1
            self.stack.setCurrentIndex(next_idx)
            self.prev_btn.setEnabled(True)
            self.next_btn.setText("Install" if next_idx == 4 else "Next")
            return

        if idx == 4:
            self.stack.setCurrentIndex(5)
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self._run_install()
            return

    def _run_install(self):
        config = self._build_config()
        self.install_log.clear()
        self.worker = SetupWorker(config)
        self.worker.log_line.connect(self._append_log)
        self.worker.finished.connect(self._install_finished)
        self.worker.start()

    def _append_log(self, line: str):
        self.install_log.append(line)

    def _install_finished(self, ok: bool, message: str):
        if ok:
            cfg = self._build_config()
            lan = get_lan_ip()
            port = cfg.server_port
            self.summary_label.setText(
                f"Dashboard: http://localhost:{port}/\n"
                f"Client server URL: http://{lan}:{port}\n"
                f"Admin login: {cfg.admin_username}"
            )
            self.stack.setCurrentIndex(6)
            self.next_btn.setEnabled(False)
        else:
            QMessageBox.critical(self, "Setup Failed", message)
            self.stack.setCurrentIndex(4)
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)
            self.next_btn.setText("Retry Install")

    def _finish(self):
        self._allow_close = True
        self.close()
        if self.on_complete:
            self.on_complete()

    def closeEvent(self, event):
        if not self._allow_close and self.stack.currentIndex() < 6:
            event.ignore()
            QMessageBox.information(
                self,
                "Setup Required",
                "Please complete installation setup before closing.",
            )
        else:
            super().closeEvent(event)


def needs_setup() -> bool:
    from services.install_config import is_configured

    return not is_configured()
