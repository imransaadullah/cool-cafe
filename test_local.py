#!/usr/bin/env python3
"""
Local Testing Script for CyberCafe Management System
Automates setup and starts all services for testing
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(text):
    print(f"\n→ {text}")


def check_command(cmd):
    """Check if a command is available."""
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.returncode == 0


def run_command(cmd, description, cwd=None):
    """Run a command and print output."""
    print_step(description)
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error: {result.stderr}")
        return False
    print(f"  Success")
    return True


def main():
    print_header("CyberCafe Local Testing Setup")
    
    project_root = Path(__file__).parent
    
    # Step 1: Check prerequisites
    print_step("Checking prerequisites...")
    
    if not check_command("python --version"):
        print("  ❌ Python not found. Install Python 3.11+")
        return 1
    print("  ✓ Python found")
    
    if not check_command("psql --version"):
        print("  ⚠ PostgreSQL not found. Install from postgresql.org")
        print("    Or use Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15")
    else:
        print("  ✓ PostgreSQL found")
    
    if not check_command("node --version"):
        print("  ⚠ Node.js not found. Install from nodejs.org")
    else:
        print("  ✓ Node.js found")
    
    # Step 2: Create .env if not exists
    print_step("Setting up environment...")
    
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print("  ✓ Created .env from .env.example")
            print("  ⚠ Edit .env with your database credentials")
        else:
            print("  ❌ .env.example not found")
    else:
        print("  ✓ .env already exists")
    
    # Step 3: Install Python dependencies
    print_step("Installing Python dependencies...")
    
    req_files = [
        ("local_server/requirements.txt", "Local Server"),
    ]
    
    for req_file, name in req_files:
        req_path = project_root / req_file
        if req_path.exists():
            subprocess.run(
                f"pip install -r {req_file}",
                shell=True,
                cwd=project_root,
                capture_output=True
            )
            print(f"  ✓ {name} dependencies installed")
    
    # Install prisma
    subprocess.run("pip install prisma", shell=True, capture_output=True)
    print("  ✓ Prisma installed")
    
    # Install PyQt6 for client
    subprocess.run("pip install PyQt6", shell=True, capture_output=True)
    print("  ✓ PyQt6 installed")
    
    # Step 4: Setup database
    print_step("Setting up database...")
    
    # Generate Prisma client
    result = subprocess.run(
        "prisma generate",
        shell=True,
        cwd=project_root,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("  ✓ Prisma client generated")
    else:
        print(f"  ⚠ Prisma generate issue: {result.stderr[:100]}")
    
    # Push schema
    result = subprocess.run(
        "prisma db push",
        shell=True,
        cwd=project_root,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("  ✓ Database schema pushed")
    else:
        print(f"  ⚠ Database push issue: {result.stderr[:100]}")
        print("    Make sure PostgreSQL is running and .env is configured")
    
    # Step 5: Install dashboard dependencies
    print_step("Installing dashboard dependencies...")
    
    dashboard_dir = project_root / "dashboard/frontend"
    if dashboard_dir.exists():
        subprocess.run(
            "npm install",
            shell=True,
            cwd=dashboard_dir,
            capture_output=True
        )
        print("  ✓ Dashboard dependencies installed")
    
    # Step 6: Create admin user
    print_step("Creating admin user...")
    
    create_admin_script = project_root / "scripts/create_admin.py"
    if create_admin_script.exists():
        result = subprocess.run(
            f"python {create_admin_script}",
            shell=True,
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("  ✓ Admin user created")
        else:
            print(f"  ⚠ Admin creation: {result.stdout[:100]}")
    
    # Step 7: Create desktop shortcuts
    print_step("Creating desktop shortcuts...")
    
    create_shortcuts_script = project_root / "create_shortcuts.py"
    if create_shortcuts_script.exists():
        subprocess.run(
            f"python {create_shortcuts_script}",
            shell=True,
            cwd=project_root,
            capture_output=True
        )
        print("  ✓ Desktop shortcuts created")
    
    # Summary
    print_header("Setup Complete!")
    
    print("""
To start the system, open 3 terminal windows:

TERMINAL 1 - Local Server:
  cd local_server
  uvicorn app.main:app --reload --port 8000

TERMINAL 2 - Dashboard:
  cd dashboard/frontend
  npm run dev

TERMINAL 3 - Client (optional):
  cd client
  python main.py

Access Points:
  • Server API:  http://localhost:8000
  • API Docs:    http://localhost:8000/docs
  • Dashboard:   http://localhost:7842

Default Login:
  • Username: admin
  • Password: admin123
    """)
    
    # Ask to start services
    response = input("Start services now? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\nStarting services...")
        print("Press Ctrl+C to stop all services\n")
        
        # Start servers in background
        server_proc = subprocess.Popen(
            "uvicorn local_server.app.main:app --reload --port 8000",
            shell=True,
            cwd=project_root
        )
        
        dashboard_proc = subprocess.Popen(
            "npm run dev",
            shell=True,
            cwd=dashboard_dir
        )
        
        print("Services started!")
        print("  • Server: http://localhost:8000")
        print("  • Dashboard: http://localhost:7842")
        print("\nPress Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping services...")
            server_proc.terminate()
            dashboard_proc.terminate()
            print("Done!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
