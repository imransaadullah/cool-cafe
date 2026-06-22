"""
Windows Service for CyberCafe Server
Ensures the server application is always running
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
    filename=str(Path(__file__).parent / "server_service.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class CyberCafeServerService(win32serviceutil.ServiceFramework):
    """Windows Service that monitors and restarts the CyberCafe server."""
    
    _svc_name_ = "CyberCafeServer"
    _svc_display_name_ = "CyberCafe Server"
    _svc_description_ = "Manages the CyberCafe Server application"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.process = None
        self.server_path = self._get_server_path()
    
    def _get_server_path(self) -> str:
        """Get the path to the server manager executable."""
        try:
            app_dir = Path(__file__).resolve().parents[1]
        except Exception:
            app_dir = Path(r"C:\Program Files\CyberCafe Server")

        packaged = app_dir / "CyberCafe Server.exe"
        if packaged.exists():
            return str(packaged)

        default_path = Path(r"C:\Program Files\CyberCafe Server\CyberCafe Server.exe")
        if default_path.exists():
            return str(default_path)

        relative = app_dir / "server_manager.py"
        if relative.exists():
            return str(relative)

        return str(packaged)
    
    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self._stop_server()
    
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
            
            # Check if server is running
            if not self._is_server_running():
                logging.info("Server not running, starting...")
                self._start_server()
            
            # Wait before next check
            time.sleep(10)
    
    def _is_server_running(self) -> bool:
        """Check if the server process is running."""
        if self.process and self.process.poll() is None:
            return True
        
        # Check by process name
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq CyberCafe Server.exe"],
                capture_output=True,
                text=True,
            )
            return "CyberCafe Server.exe" in result.stdout
        except Exception:
            return False
    
    def _start_server(self):
        """Start the server application."""
        try:
            if self.server_path.endswith(".py"):
                self.process = subprocess.Popen(
                    [sys.executable, self.server_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                self.process = subprocess.Popen(
                    [self.server_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            logging.info(f"Server started with PID: {self.process.pid}")
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
    
    def _stop_server(self):
        """Stop the server application."""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
            # Also kill by name
            subprocess.run(
                ["taskkill", "/F", "/IM", "CyberCafe Server.exe"],
                capture_output=True,
            )
            logging.info("Server stopped")
        except Exception as e:
            logging.error(f"Failed to stop server: {e}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CyberCafeServerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CyberCafeServerService)
