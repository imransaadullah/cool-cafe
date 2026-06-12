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
import sysconfig
from pathlib import Path
from dotenv import load_dotenv


def _python_scripts_dirs():
    """Return existing Scripts directories for this Python install."""
    dirs = []
    seen = set()

    def add(path: Path):
        key = str(path).lower()
        if path.exists() and key not in seen:
            seen.add(key)
            dirs.append(path)

    try:
        import site

        add(Path(site.getusersitepackages()).parent / "Scripts")
    except Exception:
        pass

    try:
        add(Path(sysconfig.get_path("scripts")))
    except Exception:
        pass

    return dirs


def ensure_prisma_path():
    """Put Python Scripts dir on PATH so prisma-client-py is found."""
    path = os.environ.get("PATH", "")
    additions = []
    for scripts in _python_scripts_dirs():
        scripts_str = str(scripts)
        if scripts_str.lower() not in path.lower():
            additions.append(scripts_str)
    if additions:
        os.environ["PATH"] = os.pathsep.join(additions) + os.pathsep + path


def run(cmd, cwd=None):
    """Run command, return (success, output)."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return result.returncode == 0, result.stdout + result.stderr


def run_prisma():
    """Generate Prisma client and push schema to the database."""
    ensure_prisma_path()

    print("\n[prisma] Pushing schema to database...")
    success, output = run(
        f'"{sys.executable}" -m prisma db push --accept-data-loss --skip-generate'
    )
    if not success:
        print(output.strip() or "  Failed (no output)")
        return False
    print("  Done")

    print("\n[prisma] Generating Prisma client...")
    success, output = run(f'"{sys.executable}" -m prisma generate')
    if not success:
        print(output.strip() or "  Failed (no output)")
        return False
    print("  Done")
    return True


def main():
    root = Path(__file__).parent
    os.chdir(root)
    
    # Load .env
    load_dotenv()
    ensure_prisma_path()

    if "--prisma-only" in sys.argv:
        sys.exit(0 if run_prisma() else 1)

    print("=" * 50)
    print("  CyberCafe Setup")
    print("=" * 50)
    
    # 1. Install Python dependencies
    print("\n[1/6] Installing Python dependencies...")
    run("pip install -r local_server/requirements.txt")
    run("pip install -r client/requirements.txt")
    run("pip install prisma")
    run("pip install python-dotenv")
    run("pip install psycopg2-binary")
    print("  Done")

    # 2. Create database if not exists
    print("\n[2/6] Creating database...")
    
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
    
    # 3. Prisma db push + generate
    print("\n[3/6] Syncing Prisma schema and client...")
    if not run_prisma():
        print("  Prisma sync failed. Fix errors above and try again.")
        sys.exit(1)

    # 4. Create admin user
    print("\n[4/6] Creating admin user...")
    run("python scripts/create_admin.py")
    print("  Done")
    
    # 5. Install dashboard dependencies
    print("\n[5/6] Installing dashboard dependencies...")
    dashboard_dir = Path("dashboard/frontend")
    if dashboard_dir.exists():
        run("npm install", cwd=dashboard_dir)
    print("  Done")

    # 6. Quick sanity check
    print("\n[6/6] Verifying setup...")
    checks = [
        ("PyQt6", "import PyQt6"),
        ("requests", "import requests"),
        ("prisma", "import prisma"),
    ]
    for name, stmt in checks:
        ok, _ = run(f'python -c "{stmt}"')
        print(f"  {'OK' if ok else 'MISSING'}: {name}")
    
    print("\n" + "=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print("""
Start the system:

  Option 1 (automated):
    start_test.bat

  Option 2 (manual):
    Terminal 1: python -m uvicorn local_server.app.main:app --reload --reload-dir local_server --reload-dir shared --host 0.0.0.0 --port 8000
    Terminal 2: cd dashboard/frontend && npm run dev
    Client PC:  client\\start_client.bat   (or client\\main.pyw)

  Reset a client PC:
    client\\reset_client.bat

Login:
  Username: admin
  Password: admin123
""")


if __name__ == "__main__":
    main()
