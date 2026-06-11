#!/bin/bash

# CyberCafe Local Server Installation Script
# Tested on Ubuntu 20.04/22.04 and Debian 11/12

set -e

echo "=== CyberCafe Local Server Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Python 3.11
echo "Installing Python 3.11..."
apt-get install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL
echo "Installing PostgreSQL..."
apt-get install -y postgresql postgresql-contrib libpq-dev

# Create database
echo "Creating database..."
su - postgres -c "psql -c \"CREATE USER cybercafe WITH PASSWORD 'cybercafe';\""
su - postgres -c "psql -c \"CREATE DATABASE cybercafe OWNER cybercafe;\""

# Create application directory
echo "Setting up application..."
APP_DIR="/opt/cybercafe"
mkdir -p $APP_DIR

# Copy application files
cp -r ../../local_server $APP_DIR/
cp -r ../../shared $APP_DIR/

# Create virtual environment
cd $APP_DIR
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r local_server/requirements.txt

# Create environment file
cat > $APP_DIR/.env << EOF
DATABASE_URL=postgresql://cybercafe:cybercafe@localhost:5432/cybercafe
SECRET_KEY=$(openssl rand -hex 32)
DEPLOYMENT_MODE=local_only
HOST=0.0.0.0
PORT=8000
EOF

# Create systemd service
cat > /etc/systemd/system/cybercafe.service << EOF
[Unit]
Description=CyberCafe Local Server
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/uvicorn local_server.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable cybercafe
systemctl start cybercafe

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Service Status: systemctl status cybercafe"
echo "View Logs: journalctl -u cybercafe -f"
echo "API Docs: http://localhost:8000/api/docs"
echo ""
echo "Default Admin Login:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Change password immediately!"
