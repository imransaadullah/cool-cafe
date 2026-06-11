#!/usr/bin/env python3
"""
Build script for CyberCafe Management System
Creates installable packages for both server and client
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, description, cwd=None):
    """Run a shell command."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error: Command failed with return code {result.returncode}")
        return False
    return True


def clean_directories():
    """Clean build directories."""
    print("\nCleaning build directories...")
    for dir_name in ["build", "dist", "installer_output"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}")


def build_server():
    """Build the server application."""
    print("\n" + "="*60)
    print("  BUILDING CYBERCAFE SERVER")
    print("="*60)
    
    # Install dependencies
    run_command(
        "pip install -r requirements.txt",
        "Installing server dependencies",
        cwd="local_server"
    )
    
    # Install PyInstaller
    run_command("pip install pyinstaller", "Installing PyInstaller")
    
    # Build with PyInstaller
    run_command(
        "pyinstaller build.spec",
        "Building server executable",
        cwd="local_server"
    )
    
    print("\n✓ Server build complete!")
    print(f"  Output: local_server/dist/CyberCafe Server/")


def build_client():
    """Build the client application."""
    print("\n" + "="*60)
    print("  BUILDING CYBERCAFE CLIENT")
    print("="*60)
    
    # Install dependencies
    run_command(
        "pip install -r requirements.txt",
        "Installing client dependencies",
        cwd="client"
    )
    
    # Build with PyInstaller
    run_command(
        "pyinstaller build.spec",
        "Building client executable",
        cwd="client"
    )
    
    print("\n✓ Client build complete!")
    print(f"  Output: client/dist/CyberCafe Client/")


def build_dashboard():
    """Build the Vue.js dashboard."""
    print("\n" + "="*60)
    print("  BUILDING DASHBOARD")
    print("="*60)
    
    # Check if npm is available
    result = subprocess.run("npm --version", shell=True, capture_output=True)
    if result.returncode != 0:
        print("  npm not found, skipping dashboard build")
        return
    
    # Install dependencies
    run_command(
        "npm install",
        "Installing dashboard dependencies",
        cwd="dashboard/frontend"
    )
    
    # Build
    run_command(
        "npm run build",
        "Building dashboard",
        cwd="dashboard/frontend"
    )
    
    print("\n✓ Dashboard build complete!")
    print(f"  Output: dashboard/frontend/dist/")


def create_installer():
    """Create Windows installer using Inno Setup."""
    print("\n" + "="*60)
    print("  CREATING INSTALLERS")
    print("="*60)
    
    # Check if Inno Setup is available
    result = subprocess.run('where iscc', shell=True, capture_output=True)
    if result.returncode != 0:
        print("  Inno Setup not found, skipping installer creation")
        print("  Download from: https://jrsoftware.org/isinfo.php")
        return
    
    # Build server installer
    run_command(
        'iscc server_setup.iss',
        "Creating server installer",
        cwd="deploy/installer"
    )
    
    # Build client installer
    run_command(
        'iscc client_setup.iss',
        "Creating client installer",
        cwd="deploy/installer"
    )
    
    print("\n✓ Installers created!")
    print(f"  Output: deploy/installer/installer_output/")


def create_portable_packages():
    """Create portable (zip) packages."""
    print("\n" + "="*60)
    print("  CREATING PORTABLE PACKAGES")
    print("="*60)
    
    os.makedirs("releases", exist_ok=True)
    
    # Server portable
    if os.path.exists("local_server/dist/CyberCafe Server"):
        shutil.make_archive(
            "releases/cybercafe_server_portable",
            "zip",
            "local_server/dist",
            "CyberCafe Server"
        )
        print("  ✓ Server portable package created")
    
    # Client portable
    if os.path.exists("client/dist/CyberCafe Client"):
        shutil.make_archive(
            "releases/cybercafe_client_portable",
            "zip",
            "client/dist",
            "CyberCafe Client"
        )
        print("  ✓ Client portable package created")


def main():
    """Main build function."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CyberCafe Management System - Build Script         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Get build options
    print("Build options:")
    print("  1. Build all (Server + Client + Dashboard)")
    print("  2. Build Server only")
    print("  3. Build Client only")
    print("  4. Build Dashboard only")
    print("  5. Create installers")
    print("  6. Clean and rebuild all")
    
    choice = input("\nSelect option (1-6) [1]: ").strip() or "1"
    
    os.chdir(Path(__file__).parent)
    
    if choice == "1":
        build_server()
        build_client()
        build_dashboard()
        create_portable_packages()
    elif choice == "2":
        build_server()
    elif choice == "3":
        build_client()
    elif choice == "4":
        build_dashboard()
    elif choice == "5":
        create_installer()
    elif choice == "6":
        clean_directories()
        build_server()
        build_client()
        build_dashboard()
        create_portable_packages()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                      Build Complete!                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Output directories:                                        ║
║    - local_server/dist/     (Server executable)             ║
║    - client/dist/           (Client executable)             ║
║    - dashboard/frontend/dist/ (Dashboard web app)           ║
║    - releases/              (Portable packages)             ║
║    - deploy/installer/installer_output/ (Installers)        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
