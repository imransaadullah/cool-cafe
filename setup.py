#!/usr/bin/env python3
"""
CyberCafe Setup Script
Run this to idempotently setup the entire system.
Safe to run multiple times.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv


def run(cmd, cwd=None):
    """Run command, return (success, output)."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout + result.stderr


def main():
    root = Path(__file__).parent
    os.chdir(root)
    
    # Load .env
    load_dotenv()
    
    # Ensure pip-installed console scripts (prisma, prisma-client-py) are on PATH
    try:
        import site
        scripts_dir = Path(site.getusersitepackages()).parent / "Scripts"
        if scripts_dir.exists():
            os.environ["PATH"] = f"{scripts_dir}{os.pathsep}{os.environ['PATH']}"
    except Exception:
        pass
    
    print("=" * 50)
    print("  CyberCafe Setup")
    print("=" * 50)
    
    # 1. Install Python dependencies
    print("\n[1/6] Installing Python dependencies...")
    run("pip install -r local_server/requirements.txt")
    run("pip install prisma")
    run("pip install python-dotenv")
    run("pip install psycopg2-binary")
    run("pip install PyQt6")
    print("  Done")
    
    # 2. Generate Prisma client
    print("\n[2/6] Generating Prisma client...")
    run("python -m prisma generate")
    print("  Done")
    
    # 3. Create database if not exists
    print("\n[3/6] Creating database...")
    
    db_url = os.environ.get("DATABASE_URL", "")
    
    try:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(db_url)
        db_name = parsed.path.lstrip("/")
        db_host = parsed.hostname or "localhost"
        db_port = parsed.port or 5432
        db_user = parsed.username or "postgres"
        db_password = unquote(parsed.password or "")  # Decode URL-encoded password
        
        print(f"  Database: {db_name} on {db_host}:{db_port}")
        
        # Try to create database using psql
        create_cmd = f'psql -h {db_host} -p {db_port} -U {db_user} -c "CREATE DATABASE {db_name};"'
        
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            print(f"  Database '{db_name}' created")
        elif "already exists" in result.stderr:
            print(f"  Database '{db_name}' already exists")
        else:
            print(f"  Warning: {result.stderr.strip()[:100]}")
            
    except Exception as e:
        print(f"  Warning: Could not create database: {e}")
    
    # 4. Push schema to database
    print("\n[4/6] Pushing schema to database...")
    success, output = run("python -m prisma db push")
    if success:
        print("  Done")
    else:
        print(f"  Warning: {output.strip()[:200]}")
    
    # 5. Create admin user
    print("\n[5/6] Creating admin user...")
    run("python scripts/create_admin.py")
    print("  Done")
    
    # 6. Install dashboard dependencies
    print("\n[6/6] Installing dashboard dependencies...")
    dashboard_dir = Path("dashboard/frontend")
    if dashboard_dir.exists():
        run("npm install", cwd=dashboard_dir)
    print("  Done")
    
    print("\n" + "=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print("""
Start the system:

  Option 1 (automated):
    start_test.bat

  Option 2 (manual - 3 terminals):
    Terminal 1: cd local_server && uvicorn app.main:app --reload --port 8000
    Terminal 2: cd dashboard/frontend && npm run dev
    Terminal 3: cd client && python main.py

Login:
  Username: admin
  Password: admin123
""")


if __name__ == "__main__":
    main()
