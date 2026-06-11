#!/usr/bin/env python3
"""
Create desktop shortcuts for CyberCafe applications
"""

import os
import sys
from pathlib import Path


def create_shortcut(target, shortcut_name, icon=None, working_dir=None):
    """Create a Windows desktop shortcut."""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
        
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = working_dir or os.path.dirname(target)
        if icon:
            shortcut.IconLocation = icon
        shortcut.save()
        
        print(f"  Created shortcut: {shortcut_name}")
        return True
    except ImportError:
        print("  winshell not installed. Install with: pip install winshell")
        return False
    except Exception as e:
        print(f"  Error creating shortcut: {e}")
        return False


def create_shortcuts_via_registry():
    """Create shortcuts using registry (alternative method)."""
    import winreg
    
    # Get desktop path
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    desktop = winreg.QueryValueEx(key, "Desktop")[0]
    winreg.CloseKey(key)
    
    # Create shortcuts using VBScript
    server_exe = os.path.abspath("local_server/dist/CyberCafe Server/CyberCafe Server.exe")
    client_exe = os.path.abspath("client/dist/CyberCafe Client/CyberCafe Client.exe")
    
    if os.path.exists(server_exe):
        vbs_content = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop}\\CyberCafe Server.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{server_exe}"
oLink.WorkingDirectory = "{os.path.dirname(server_exe)}"
oLink.Save
'''
        with open("create_shortcut.vbs", "w") as f:
            f.write(vbs_content)
        os.system("cscript //nologo create_shortcut.vbs")
        os.remove("create_shortcut.vbs")
        print("  Created shortcut: CyberCafe Server")
    
    if os.path.exists(client_exe):
        vbs_content = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop}\\CyberCafe Client.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{client_exe}"
oLink.WorkingDirectory = "{os.path.dirname(client_exe)}"
oLink.Save
'''
        with open("create_shortcut.vbs", "w") as f:
            f.write(vbs_content)
        os.system("cscript //nologo create_shortcut.vbs")
        os.remove("create_shortcut.vbs")
        print("  Created shortcut: CyberCafe Client")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         CyberCafe - Desktop Shortcuts Creator               ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print("Creating desktop shortcuts...")
    
    # Try winshell first, fallback to registry method
    try:
        import winshell
        from win32com.client import Dispatch
        
        server_exe = os.path.abspath("local_server/dist/CyberCafe Server/CyberCafe Server.exe")
        client_exe = os.path.abspath("client/dist/CyberCafe Client/CyberCafe Client.exe")
        
        if os.path.exists(server_exe):
            create_shortcut(server_exe, "CyberCafe Server")
        
        if os.path.exists(client_exe):
            create_shortcut(client_exe, "CyberCafe Client")
            
    except ImportError:
        print("  Using alternative method...")
        create_shortcuts_via_registry()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                   Shortcuts Created!                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  You should now see shortcuts on your desktop:              ║
║    - CyberCafe Server                                       ║
║    - CyberCafe Client                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
