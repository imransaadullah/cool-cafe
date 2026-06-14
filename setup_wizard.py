#!/usr/bin/env python3
"""
Interactive Setup Wizard for CyberCafe Management System
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           CyberCafe Management System - Setup Wizard         ║
╚══════════════════════════════════════════════════════════════╝
    """)


def get_setup_mode():
    print("\n📋 SETUP MODE")
    print("-" * 50)
    print("1. Single Cafe (Local Server only)")
    print("2. Multi-Cafe (Local + Global Server)")
    print("3. Client Only (Install on user PCs)")
    print("4. Docker Setup")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            return int(choice)
        print("Invalid option. Please try again.")


def setup_local_server():
    print("\n🖥️  LOCAL SERVER SETUP")
    print("-" * 50)
    
    # Get configuration
    server_url = input("Server host [0.0.0.0]: ").strip() or "0.0.0.0"
    port = input("Port [8000]: ").strip() or "8000"
    db_url = input("Database URL [postgresql://postgres:postgres@localhost:5432/cybercafe]: ").strip()
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/cybercafe"
    
    # Create .env file
    env_content = f"""DATABASE_URL={db_url}
SECRET_KEY={os.urandom(32).hex()}
HOST={server_url}
PORT={port}
DEPLOYMENT_MODE=local_only
CORS_ORIGINS=["http://localhost:7842"]
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n✅ .env file created")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "prisma"], check=True)
    
    # Generate Prisma client
    print("\n🔧 Generating Prisma client...")
    subprocess.run(["prisma", "generate"], check=True)
    
    # Push database schema
    print("\n🗄️  Setting up database...")
    subprocess.run(["prisma", "db", "push"], check=True)
    
    # Create admin user
    print("\n👤 Creating admin user...")
    subprocess.run([sys.executable, "../scripts/create_admin.py"], check=True)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Setup Complete!                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Start the server:                                          ║
║    uvicorn app.main:app --host {server_url} --port {port}          ║
║                                                              ║
║  API Documentation:                                         ║
║    http://localhost:{port}/api/docs                                  ║
║                                                              ║
║  Default Login:                                             ║
║    Username: admin                                          ║
║    Password: admin123                                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def setup_global_server():
    print("\n🌐 GLOBAL SERVER SETUP")
    print("-" * 50)
    
    # Get configuration
    server_url = input("Server host [0.0.0.0]: ").strip() or "0.0.0.0"
    port = input("Port [8001]: ").strip() or "8001"
    db_url = input("Database URL [postgresql://postgres:postgres@localhost:5432/cybercafe_global]: ").strip()
    if not db_url:
        db_url = "postgresql://postgres:postgres@localhost:5432/cybercafe_global"
    
    # Create .env file
    env_content = f"""DATABASE_URL={db_url}
SECRET_KEY={os.urandom(32).hex()}
HOST={server_url}
PORT={port}
CORS_ORIGINS=["http://localhost:7842"]
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n✅ .env file created")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "prisma"], check=True)
    
    # Generate Prisma client
    print("\n🔧 Generating Prisma client...")
    subprocess.run(["prisma", "generate"], check=True)
    
    # Push database schema
    print("\n🗄️  Setting up database...")
    subprocess.run(["prisma", "db", "push"], check=True)
    
    # Create admin user
    print("\n👤 Creating admin user...")
    subprocess.run([sys.executable, "../scripts/create_admin.py"], check=True)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Setup Complete!                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Start the server:                                          ║
║    uvicorn app.main:app --host {server_url} --port {port}          ║
║                                                              ║
║  API Documentation:                                         ║
║    http://localhost:{port}/api/docs                                  ║
║                                                              ║
║  Now configure your Local Servers to connect to this        ║
║  Global Server by setting:                                  ║
║    GLOBAL_SERVER_URL=http://<this_server_ip>:{port}           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def setup_client():
    print("\n💻 CLIENT SETUP")
    print("-" * 50)
    
    # Get configuration
    server_url = input("Local Server URL [http://localhost:8000]: ").strip()
    if not server_url:
        server_url = "http://localhost:8000"
    
    pc_id = input("PC ID [1]: ").strip()
    if not pc_id:
        pc_id = "1"
    
    # Create config file
    import json
    config = {
        "server_url": server_url,
        "pc_id": int(pc_id),
        "branch_id": 1,
        "heartbeat_interval": 5,
        "offline_mode": False,
        "filtering": {
            "dns_blocking": True,
            "process_blocking": True,
            "url_filtering": True,
        },
        "ui": {
            "fullscreen": True,
            "always_on_top": True,
            "theme": "dark",
        },
    }
    
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ config.json created")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    Setup Complete!                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Build the client:                                          ║
║    pyinstaller build.spec                                   ║
║                                                              ║
║  Or run directly:                                           ║
║    python main.py                                           ║
║                                                              ║
║  To install watchdog service (Windows):                     ║
║    cd services                                              ║
║    install_watchdog.bat (as Administrator)                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def setup_docker():
    print("\n🐳 DOCKER SETUP")
    print("-" * 50)
    
    # Create .env file
    env_content = f"""SECRET_KEY={os.urandom(32).hex()}
DATABASE_URL=postgresql://postgres:postgres@local_db:5432/cybercafe
"""
    
    with open("deploy/docker/.env", "w") as f:
        f.write(env_content)
    
    print("\n✅ .env file created")
    
    # Start docker-compose
    print("\n🚀 Starting Docker containers...")
    subprocess.run(
        ["docker-compose", "up", "-d"],
        cwd="deploy/docker",
        check=True,
    )
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    Setup Complete!                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Services running:                                         ║
║    - Local Server: http://localhost:8000                   ║
║    - Global Server: http://localhost:8001                   ║
║    - Dashboard: http://localhost:7842                       ║
║    - PostgreSQL: localhost:5432                             ║
║                                                              ║
║  View logs:                                                 ║
║    docker-compose -f deploy/docker/docker-compose.yml logs  ║
║                                                              ║
║  Stop services:                                             ║
║    docker-compose -f deploy/docker/docker-compose.yml down  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def main():
    print_header()
    
    mode = get_setup_mode()
    
    os.chdir(Path(__file__).parent)
    
    if mode == 1:
        os.chdir("local_server")
        setup_local_server()
    elif mode == 2:
        # Setup global server first
        setup_global = input("\nSetup Global Server first? (y/n) [y]: ").strip().lower()
        if setup_global != "n":
            os.chdir("global_server")
            setup_global_server()
        
        # Then setup local server
        os.chdir("local_server")
        setup_local_server()
    elif mode == 3:
        os.chdir("client")
        setup_client()
    elif mode == 4:
        setup_docker()


if __name__ == "__main__":
    main()
