import subprocess
import time
import os
import sys
from typing import Optional


class Watchdog:
    """Watchdog service that ensures the client application is running."""
    
    def __init__(self, client_path: str = "main.py"):
        self.client_path = client_path
        self.process: Optional[subprocess.Popen] = None
        self.running = True
    
    def start_client(self):
        """Start the client application."""
        python_path = sys.executable
        self.process = subprocess.Popen(
            [python_path, self.client_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"Client started with PID: {self.process.pid}")
    
    def is_client_running(self) -> bool:
        """Check if the client process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def restart_client(self):
        """Restart the client application."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        
        self.start_client()
    
    def run(self):
        """Main watchdog loop."""
        self.start_client()
        
        while self.running:
            if not self.is_client_running():
                print("Client not running, restarting...")
                self.start_client()
            
            time.sleep(5)  # Check every 5 seconds
    
    def stop(self):
        """Stop the watchdog."""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    watchdog = Watchdog()
    try:
        watchdog.run()
    except KeyboardInterrupt:
        watchdog.stop()
