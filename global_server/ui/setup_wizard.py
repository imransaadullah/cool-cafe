"""First-run setup wizard for CyberCafe Global Server."""

from __future__ import annotations

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

GLOBAL_SERVER = Path(__file__).resolve().parents[1]
ROOT = GLOBAL_SERVER.parent
for p in (str(ROOT), str(GLOBAL_SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.setup_runner import GlobalSetupConfig, run_full_setup, test_database_connection


class SetupWorker(QThread):
    finished = pyqtSignal(bool, str)
    log_line = pyqtSignal(str)

    def __init__(self, config: GlobalSetupConfig):
        super().__init__()
        self.config = config

    def run(self):
        ok, msg = run_full_setup(self.config, log=self.log_line.emit)
        self.finished.emit(ok, msg)


class GlobalSetupWizard(QMainWindow):
    def __init__(self, on_complete=None):
        super().__init__()
        self.on_complete = on_complete
        self._allow_close = False
        self.setWindowTitle("CyberCafe Global Server — Setup")
        self.setMinimumSize(600, 520)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet("background:#1a1a2e;color:#fff;")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Global Server Setup")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        layout.addWidget(title)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self._welcome()
        self._database()
        self._org()
        self._admin()
        self._network()
        self._install()
        self._done()

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("Back")
        self.prev_btn.clicked.connect(self._prev)
        self.prev_btn.setEnabled(False)
        nav.addWidget(self.prev_btn)
        nav.addStretch()
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._next)
        self.next_btn.setStyleSheet("background:#e94560;font-weight:bold;padding:8px 20px;")
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

    def _welcome(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel(
            "Install the multi-site owner server.\n\n"
            "• Central database for all branches\n"
            "• Branch sync and owner APIs\n"
            "• Configure local servers to point here\n\n"
            "PostgreSQL must be installed and running."
        ))
        lay.addStretch()
        self.stack.addWidget(w)

    def _database(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("PostgreSQL")
        form = QFormLayout(box)
        self.db_host = QLineEdit("localhost")
        self.db_port = QSpinBox()
        self.db_port.setRange(1, 65535)
        self.db_port.setValue(5432)
        self.db_user = QLineEdit("postgres")
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_name = QLineEdit("cybercafe_global")
        form.addRow("Host:", self.db_host)
        form.addRow("Port:", self.db_port)
        form.addRow("User:", self.db_user)
        form.addRow("Password:", self.db_password)
        form.addRow("Database:", self.db_name)
        lay.addWidget(box)
        row = QHBoxLayout()
        self.db_status = QLabel("")
        btn = QPushButton("Test Connection")
        btn.clicked.connect(self._test_db)
        row.addWidget(btn)
        row.addWidget(self.db_status)
        lay.addLayout(row)
        lay.addStretch()
        self.stack.addWidget(w)

    def _org(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("Organization")
        form = QFormLayout(box)
        self.org_name = QLineEdit("My Cyber Café Chain")
        form.addRow("Organization name:", self.org_name)
        lay.addWidget(box)
        lay.addStretch()
        self.stack.addWidget(w)

    def _admin(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("Owner Account")
        form = QFormLayout(box)
        self.admin_user = QLineEdit("owner")
        self.admin_pass = QLineEdit()
        self.admin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_confirm = QLineEdit()
        self.admin_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_email = QLineEdit()
        form.addRow("Username:", self.admin_user)
        form.addRow("Password:", self.admin_pass)
        form.addRow("Confirm:", self.admin_confirm)
        form.addRow("Email:", self.admin_email)
        lay.addWidget(box)
        lay.addStretch()
        self.stack.addWidget(w)

    def _network(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("Network")
        form = QFormLayout(box)
        self.server_port = QSpinBox()
        self.server_port.setRange(1024, 65535)
        self.server_port.setValue(9000)
        form.addRow("API port:", self.server_port)
        lay.addWidget(box)
        self.auto_start_cb = QCheckBox("Start automatically when app opens")
        self.auto_start_cb.setChecked(True)
        self.open_browser_cb = QCheckBox("Open API docs in browser when started")
        self.open_browser_cb.setChecked(True)
        lay.addWidget(self.auto_start_cb)
        lay.addWidget(self.open_browser_cb)
        lay.addStretch()
        self.stack.addWidget(w)

    def _install(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Installing…"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background:#0f0f1a;color:#ccc;font-family:Consolas;")
        lay.addWidget(self.log)
        self.stack.addWidget(w)

    def _done(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.summary = QLabel("Setup complete!")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary.setStyleSheet("color:#4caf50;font-size:16px;")
        lay.addWidget(self.summary)
        btn = QPushButton("Open Global Server Manager")
        btn.clicked.connect(self._finish)
        btn.setStyleSheet("background:#4caf50;padding:12px;font-weight:bold;")
        lay.addWidget(btn)
        lay.addStretch()
        self.stack.addWidget(w)

    def _config(self) -> GlobalSetupConfig:
        return GlobalSetupConfig(
            organization_name=self.org_name.text().strip() or "Organization",
            db_host=self.db_host.text().strip() or "localhost",
            db_port=self.db_port.value(),
            db_user=self.db_user.text().strip() or "postgres",
            db_password=self.db_password.text(),
            db_name=self.db_name.text().strip() or "cybercafe_global",
            admin_username=self.admin_user.text().strip() or "owner",
            admin_password=self.admin_pass.text(),
            admin_email=self.admin_email.text().strip(),
            server_port=self.server_port.value(),
            auto_start=self.auto_start_cb.isChecked(),
            open_browser=self.open_browser_cb.isChecked(),
        )

    def _test_db(self):
        ok, msg = test_database_connection(self._config())
        self.db_status.setText(msg[:120])
        self.db_status.setStyleSheet("color:#4caf50;" if ok else "color:#e94560;")

    def _validate(self, idx: int) -> bool:
        if idx == 1:
            if not self.db_password.text():
                QMessageBox.warning(self, "Database", "Enter PostgreSQL password.")
                return False
            ok, msg = test_database_connection(self._config())
            if not ok:
                QMessageBox.warning(self, "Database", msg)
                return False
        if idx == 3:
            if len(self.admin_pass.text()) < 6:
                QMessageBox.warning(self, "Admin", "Password must be at least 6 characters.")
                return False
            if self.admin_pass.text() != self.admin_confirm.text():
                QMessageBox.warning(self, "Admin", "Passwords do not match.")
                return False
        return True

    def _prev(self):
        i = self.stack.currentIndex()
        if i > 0:
            self.stack.setCurrentIndex(i - 1)
            self.prev_btn.setEnabled(i - 1 > 0)
            self.next_btn.setText("Install" if i - 1 == 4 else "Next")

    def _next(self):
        i = self.stack.currentIndex()
        if i < 4:
            if not self._validate(i):
                return
            n = i + 1
            self.stack.setCurrentIndex(n)
            self.prev_btn.setEnabled(True)
            self.next_btn.setText("Install" if n == 4 else "Next")
            return
        if i == 4:
            self.stack.setCurrentIndex(5)
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.worker = SetupWorker(self._config())
            self.worker.log_line.connect(self.log.append)
            self.worker.finished.connect(self._installed)
            self.worker.start()

    def _installed(self, ok: bool, msg: str):
        if ok:
            c = self._config()
            self.summary.setText(
                f"API: http://localhost:{c.server_port}/api/docs\n"
                f"Owner login: {c.admin_username}\n"
                f"Point local servers to: http://YOUR-IP:{c.server_port}"
            )
            self.stack.setCurrentIndex(6)
        else:
            QMessageBox.critical(self, "Failed", msg)
            self.stack.setCurrentIndex(4)
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)

    def _finish(self):
        self._allow_close = True
        self.close()
        if self.on_complete:
            self.on_complete()

    def closeEvent(self, event):
        if not self._allow_close and self.stack.currentIndex() < 6:
            event.ignore()
        else:
            super().closeEvent(event)
