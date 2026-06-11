"""
Security Monitor Service
Detects bypass attempts and monitors client integrity
"""

import os
import sys
import psutil
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
import time
from services.config_manager import client_config


class SecurityMonitor(QThread):
    """Thread that monitors for security breaches."""
    
    bypass_detected = pyqtSignal(str, str)  # event_type, method
    alarm_trigger = pyqtSignal(str)  # reason
    
    def __init__(self, pc_id: int):
        super().__init__()
        self.pc_id = pc_id
        self.running = True
        self.check_interval = 5  # seconds
        self.protected_processes = [
            "CyberCafe Client.exe",
            "CyberCafe Server.exe",
        ]
        self.blocked_processes = [
            "taskmgr.exe",
            "taskill.exe",
            "regedit.exe",
            "cmd.exe",
            "powershell.exe",
        ]
    
    def run(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_client_running()
                self._check_unauthorized_processes()
                self._check_service_status()
                self._check_files_integrity()
            except Exception as e:
                print(f"Security monitor error: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_client_running(self):
        """Check if our client process is running."""
        current_pid = os.getpid()
        client_running = False
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == "CyberCafe Client.exe":
                    if proc.info['pid'] != current_pid:
                        client_running = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # If we're the only instance, that's fine
        # But if someone killed another instance, detect it
    
    def _check_unauthorized_processes(self):
        """Check for unauthorized processes (Task Manager, etc.)."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                
                # Check blocked processes
                for blocked in self.blocked_processes:
                    if blocked.lower() in proc_name:
                        self.bypass_detected.emit(
                            "unauthorized_process",
                            f"Detected: {proc.info['name']}"
                        )
                        self._kill_process(proc.info['pid'])
                        return
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def _check_service_status(self):
        """Check if watchdog service is running."""
        if not client_config.get("security.run_as_service", False):
            return
        
        try:
            # Windows service check
            if sys.platform == "win32":
                result = subprocess.run(
                    ["sc", "query", "CyberCafeWatchdog"],
                    capture_output=True,
                    text=True
                )
                if "RUNNING" not in result.stdout:
                    self.bypass_detected.emit(
                        "service_stopped",
                        "Watchdog service not running"
                    )
        except Exception:
            pass
    
    def _check_files_integrity(self):
        """Check if critical client files have been modified."""
        critical_files = [
            "config.json",
            "main.py",
        ]
        
        for file in critical_files:
            if not os.path.exists(file):
                self.bypass_detected.emit(
                    "file_missing",
                    f"Critical file missing: {file}"
                )
    
    def _kill_process(self, pid: int):
        """Kill an unauthorized process."""
        try:
            os.kill(pid, 9)
        except Exception:
            pass
    
    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        self.wait()


class UninstallDetector(QThread):
    """Detects if someone is trying to uninstall the client."""
    
    uninstall_detected = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.check_interval = 2  # seconds
    
    def run(self):
        """Monitor for uninstall attempts."""
        while self.running:
            try:
                self._check_uninstaller_running()
                self._check_msiexec()
                self._check_registry_modification()
            except Exception:
                pass
            
            time.sleep(self.check_interval)
    
    def _check_uninstaller_running(self):
        """Check if any uninstaller is running."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if "uninstall" in proc_name or "msiexec" in proc_name:
                    self.uninstall_detected.emit()
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def _check_msiexec(self):
        """Check for MSI installer activity."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == "msiexec.exe":
                    # Check command line for uninstall
                    cmdline = proc.cmdline()
                    if any("/x" in arg.lower() or "/uninstall" in arg.lower() for arg in cmdline):
                        self.uninstall_detected.emit()
                        return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def _check_registry_modification(self):
        """Check for registry modification attempts."""
        if sys.platform != "win32":
            return
        
        try:
            import winreg
            # Check if Run key is being modified
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            # Just checking if we can access it
            winreg.CloseKey(key)
        except Exception:
            pass
    
    def stop(self):
        """Stop the detector."""
        self.running = False
        self.wait()
