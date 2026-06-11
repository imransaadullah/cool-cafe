"""
Windows Service Watchdog for CyberCafe Client
Ensures the client application is always running
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import sys
import os
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    filename=str(Path(__file__).parent / "watchdog.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class CyberCafeWatchdog(win32serviceutil.ServiceFramework):
    """Windows Service that monitors and restarts the CyberCafe client."""
    
    _svc_name_ = "CyberCafeWatchdog"
    _svc_display_name_ = "CyberCafe Client Watchdog"
    _svc_description_ = "Monitors and restarts the CyberCafe client application"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None
        self.client_path = self._get_client_path()
    
    def _get_client_path(self) -> str:
        """Get the path to the client executable."""
        # Default installation path
        default_path = r"C:\Program Files\CyberCafe\client\CyberCafe Client.exe"
        if os.path.exists(default_path):
            return default_path
        
        # Try relative path
        relative_path = os.path.join(os.path.dirname(__file__), "..", "client", "main.py")
        if os.path.exists(relative_path):
            return relative_path
        
        return default_path
    
    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self._stop_client()
    
    def SvcDoRun(self):
        """Main service entry point."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self._run()
    
    def _run(self):
        """Main service loop."""
        while True:
            # Check if we should stop
            if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                break
            
            # Check if client is running
            if not self._is_client_running():
                logging.info("Client not running, starting...")
                self._start_client()
            
            # Wait before next check
            time.sleep(5)
    
    def _is_client_running(self) -> bool:
        """Check if the client process is running."""
        if self.process and self.process.poll() is None:
            return True
        
        # Check by process name
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq CyberCafe Client.exe"],
                capture_output=True,
                text=True,
            )
            return "CyberCafe Client.exe" in result.stdout
        except Exception:
            return False
    
    def _start_client(self):
        """Start the client application."""
        try:
            if self.client_path.endswith(".py"):
                self.process = subprocess.Popen(
                    [sys.executable, self.client_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                self.process = subprocess.Popen(
                    [self.client_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            logging.info(f"Client started with PID: {self.process.pid}")
        except Exception as e:
            logging.error(f"Failed to start client: {e}")
    
    def _stop_client(self):
        """Stop the client application."""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
            # Also kill by name
            subprocess.run(
                ["taskkill", "/F", "/IM", "CyberCafe Client.exe"],
                capture_output=True,
            )
            logging.info("Client stopped")
        except Exception as e:
            logging.error(f"Failed to stop client: {e}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CyberCafeWatchdog)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CyberCafeWatchdog)
