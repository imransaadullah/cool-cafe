"""
CyberCafe Local Server - Desktop Application
A PyQt6-based admin panel that runs the FastAPI server in the background
"""

import sys
import os
import uvicorn
import threading
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSystemTrayIcon, QMenu, QMessageBox, QTabWidget, QGroupBox,
    QFormLayout, QLineEdit, QSpinBox, QCheckBox, QTextEdit, QFrame,
    QStatusBar, QMenuBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction, QFont, QColor, QPalette
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from shared.config import settings
from shared.database import db
from shared.qt_single_instance import QtSingleInstanceGuard, activate_application_window


class ServerSignals(QObject):
    """Signals for server communication."""
    status_update = pyqtSignal(dict)
    log_message = pyqtSignal(str)


class ServerThread(threading.Thread):
    """Thread to run FastAPI server."""
    
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.daemon = True
        self.server = None
        self.running = False
    
    def run(self):
        from local_server.app.main import app
        self.running = True
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self.server = uvicorn.Server(config)
        self.server.run()
    
    def stop(self):
        if self.server:
            self.server.should_exit = True
            self.running = False


class MainWindow(QMainWindow):
    """Main admin window."""
    
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.signals = ServerSignals()
        self.signals.log_message.connect(self.append_log)
        
        self.setWindowTitle("CyberCafe Local Server")
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()
        self.setup_system_tray()
        self.setup_menu_bar()
        self.setup_status_bar()
        
        # Load config
        self.load_config()
        
        # Timer for auto-refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)
    
    def setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Dashboard Tab
        self.setup_dashboard_tab()
        
        # PCs Tab
        self.setup_pcs_tab()
        
        # Sessions Tab
        self.setup_sessions_tab()
        
        # Codes Tab
        self.setup_codes_tab()
        
        # Logs Tab
        self.setup_logs_tab()
        
        # Settings Tab
        self.setup_settings_tab()
    
    def setup_dashboard_tab(self):
        """Setup dashboard tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Server Status
        status_group = QGroupBox("Server Status")
        status_layout = QHBoxLayout()
        
        self.server_status_label = QLabel("Stopped")
        self.server_status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
        status_layout.addWidget(self.server_status_label)
        
        self.start_btn = QPushButton("Start Server")
        self.start_btn.clicked.connect(self.start_server)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 20px;")
        status_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Server")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px 20px;")
        self.stop_btn.setEnabled(False)
        status_layout.addWidget(self.stop_btn)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Stats
        stats_group = QGroupBox("Statistics")
        stats_layout = QHBoxLayout()
        
        self.total_pcs_label = QLabel("Total PCs: 0")
        self.total_pcs_label.setStyleSheet("font-size: 16px;")
        stats_layout.addWidget(self.total_pcs_label)
        
        self.online_pcs_label = QLabel("Online: 0")
        self.online_pcs_label.setStyleSheet("font-size: 16px; color: green;")
        stats_layout.addWidget(self.online_pcs_label)
        
        self.active_sessions_label = QLabel("Active Sessions: 0")
        self.active_sessions_label.setStyleSheet("font-size: 16px; color: blue;")
        stats_layout.addWidget(self.active_sessions_label)
        
        self.revenue_label = QLabel("Revenue Today: ₦0")
        self.revenue_label.setStyleSheet("font-size: 16px; color: purple;")
        stats_layout.addWidget(self.revenue_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout()
        
        generate_codes_btn = QPushButton("Generate Codes")
        generate_codes_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        actions_layout.addWidget(generate_codes_btn)
        
        view_sessions_btn = QPushButton("View Sessions")
        view_sessions_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        actions_layout.addWidget(view_sessions_btn)
        
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_data)
        actions_layout.addWidget(refresh_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Dashboard")
    
    def setup_pcs_tab(self):
        """Setup PCs tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("PC Management"))
        
        add_pc_btn = QPushButton("+ Add PC")
        add_pc_btn.clicked.connect(self.add_pc)
        header.addWidget(add_pc_btn)
        
        layout.addLayout(header)
        
        # PC Table
        self.pc_table = QTableWidget()
        self.pc_table.setColumnCount(6)
        self.pc_table.setHorizontalHeaderLabels(["ID", "Name", "IP Address", "Status", "Session", "Actions"])
        self.pc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.pc_table)
        
        self.tabs.addTab(tab, "PCs")
    
    def setup_sessions_tab(self):
        """Setup sessions tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("Active Sessions"))
        layout.addLayout(header)
        
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(7)
        self.sessions_table.setHorizontalHeaderLabels(["ID", "PC", "Start", "Duration", "Remaining", "Status", "Actions"])
        self.sessions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sessions_table)
        
        self.tabs.addTab(tab, "Sessions")
    
    def setup_codes_tab(self):
        """Setup codes tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Generate Codes Form
        form_group = QGroupBox("Generate Code Batch")
        form_layout = QFormLayout()
        
        self.duration_combo = QSpinBox()
        self.duration_combo.setRange(5, 480)
        self.duration_combo.setValue(60)
        self.duration_combo.setSuffix(" minutes")
        form_layout.addRow("Duration:", self.duration_combo)
        
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(50)
        form_layout.addRow("Count:", self.count_spin)
        
        self.value_spin = QSpinBox()
        self.value_spin.setRange(0, 10000)
        self.value_spin.setValue(100)
        self.value_spin.setPrefix("₦")
        form_layout.addRow("Value per Code:", self.value_spin)
        
        generate_btn = QPushButton("Generate Codes")
        generate_btn.clicked.connect(self.generate_codes)
        form_layout.addRow(generate_btn)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Code Batches Table
        self.batches_table = QTableWidget()
        self.batches_table.setColumnCount(6)
        self.batches_table.setHorizontalHeaderLabels(["ID", "Duration", "Count", "Value", "Printed", "Actions"])
        self.batches_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.batches_table)
        
        self.tabs.addTab(tab, "Codes")
    
    def setup_logs_tab(self):
        """Setup logs tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("Server Logs"))
        
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.log_text)
        
        self.tabs.addTab(tab, "Logs")
    
    def setup_settings_tab(self):
        """Setup settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Server Settings
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        self.host_input = QLineEdit("0.0.0.0")
        server_layout.addRow("Host:", self.host_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(8000)
        server_layout.addRow("Port:", self.port_input)
        
        self.db_url_input = QLineEdit()
        self.db_url_input.setPlaceholderText("postgresql://user:pass@host:port/db")
        server_layout.addRow("Database URL:", self.db_url_input)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Filter Settings
        filter_group = QGroupBox("Content Filtering")
        filter_layout = QVBoxLayout()
        
        self.dns_filter_check = QCheckBox("Enable DNS Blocking")
        self.dns_filter_check.setChecked(True)
        filter_layout.addWidget(self.dns_filter_check)
        
        self.process_filter_check = QCheckBox("Enable Process Blocking")
        self.process_filter_check.setChecked(True)
        filter_layout.addWidget(self.process_filter_check)
        
        self.url_filter_check = QCheckBox("Enable URL Filtering")
        self.url_filter_check.setChecked(True)
        filter_layout.addWidget(self.url_filter_check)
        
        apply_filters_btn = QPushButton("Apply Filters")
        apply_filters_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(apply_filters_btn)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Save Button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        layout.addWidget(save_btn)
        
        layout.addStretch()
        self.tabs.addTab(tab, "Settings")
    
    def setup_menu_bar(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Server menu
        server_menu = menubar.addMenu("Server")
        
        start_action = QAction("Start Server", self)
        start_action.triggered.connect(self.start_server)
        server_menu.addAction(start_action)
        
        stop_action = QAction("Stop Server", self)
        stop_action.triggered.connect(self.stop_server)
        server_menu.addAction(stop_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def setup_system_tray(self):
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        
        # Tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        start_action = QAction("Start Server", self)
        start_action.triggered.connect(self.start_server)
        tray_menu.addAction(start_action)
        
        stop_action = QAction("Stop Server", self)
        stop_action.triggered.connect(self.stop_server)
        tray_menu.addAction(stop_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def start_server(self):
        """Start the FastAPI server."""
        if self.server_thread and self.server_thread.running:
            return
        
        host = self.host_input.text()
        port = self.port_input.value()
        
        self.append_log(f"Starting server on {host}:{port}...")
        
        self.server_thread = ServerThread(host, port)
        self.server_thread.start()
        
        self.server_status_label.setText("Running")
        self.server_status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.status_bar.showMessage(f"Server running on {host}:{port}")
        self.tray_icon.showMessage("CyberCafe Server", "Server started successfully")
    
    def stop_server(self):
        """Stop the FastAPI server."""
        if self.server_thread:
            self.append_log("Stopping server...")
            self.server_thread.stop()
            self.server_thread = None
        
        self.server_status_label.setText("Stopped")
        self.server_status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.status_bar.showMessage("Server stopped")
        self.tray_icon.showMessage("CyberCafe Server", "Server stopped")
    
    def refresh_data(self):
        """Refresh dashboard data."""
        if not self.server_thread or not self.server_thread.running:
            return
        
        try:
            import requests
            response = requests.get("http://localhost:8000/api/dashboard/overview", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.total_pcs_label.setText(f"Total PCs: {data.get('total_pcs', 0)}")
                self.online_pcs_label.setText(f"Online: {data.get('online_pcs', 0)}")
                self.active_sessions_label.setText(f"Active Sessions: {data.get('active_sessions', 0)}")
                self.revenue_label.setText(f"Revenue Today: ₦{data.get('total_revenue_today', 0):,.0f}")
        except Exception:
            pass
    
    def generate_codes(self):
        """Generate code batch."""
        self.append_log("Generating code batch...")
        # TODO: Implement code generation
        QMessageBox.information(self, "Success", "Code batch generated!")
    
    def add_pc(self):
        """Add new PC."""
        self.append_log("Adding new PC...")
        # TODO: Implement add PC dialog
        QMessageBox.information(self, "Info", "Add PC dialog coming soon!")
    
    def apply_filters(self):
        """Apply content filters."""
        self.append_log("Applying content filters...")
        QMessageBox.information(self, "Success", "Filters applied!")
    
    def save_settings(self):
        """Save settings."""
        config = {
            "host": self.host_input.text(),
            "port": self.port_input.value(),
            "dns_blocking": self.dns_filter_check.isChecked(),
            "process_blocking": self.process_filter_check.isChecked(),
            "url_filtering": self.url_filter_check.isChecked(),
        }
        
        with open("server_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        self.append_log("Settings saved")
        QMessageBox.information(self, "Success", "Settings saved!")
    
    def load_config(self):
        """Load settings."""
        if os.path.exists("server_config.json"):
            try:
                with open("server_config.json", "r") as f:
                    config = json.load(f)
                self.host_input.setText(config.get("host", "0.0.0.0"))
                self.port_input.setValue(config.get("port", 8000))
                self.dns_filter_check.setChecked(config.get("dns_blocking", True))
                self.process_filter_check.setChecked(config.get("process_blocking", True))
                self.url_filter_check.setChecked(config.get("url_filtering", True))
            except Exception:
                pass
    
    def append_log(self, message):
        """Append message to log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About CyberCafe Server",
            "CyberCafe Management System\nVersion 1.0.0\n\nA complete cyber cafe management solution."
        )
    
    def quit_app(self):
        """Quit the application."""
        self.stop_server()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Handle close event - minimize to tray."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "CyberCafe Server",
            "Server is running in the background.\nDouble-click tray icon to show window."
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CyberCafe Server")
    app.setOrganizationName("CyberCafe")

    guard = QtSingleInstanceGuard(
        "CyberCafeServerDesktop",
        on_activate=lambda: activate_application_window(),
    )
    if not guard.try_acquire():
        sys.exit(0)
    app._instance_guard = guard

    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 8px 16px;
            color: white;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QPushButton:pressed {
            background-color: #333;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #666;
        }
        QTableWidget {
            background-color: #1e1e1e;
            border: 1px solid #555;
            gridline-color: #3c3c3c;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #094771;
        }
        QHeaderView::section {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 5px;
            font-weight: bold;
        }
        QLineEdit, QSpinBox, QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 5px;
            color: white;
        }
        QTabWidget::pane {
            border: 1px solid #555;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 8px 16px;
            color: white;
        }
        QTabBar::tab:selected {
            background-color: #094771;
        }
    """)
    
    app.main_window = MainWindow()
    app.main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
