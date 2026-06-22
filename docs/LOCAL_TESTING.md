# Local Testing Guide

Test the entire CyberCafe system on a single laptop.

## Prerequisites

1. **PostgreSQL** - Install from https://www.postgresql.org/download/windows/
2. **Python 3.11+** - Install from python.org
3. **Node.js 18+** - Install from nodejs.org
4. **Git** - Optional, for cloning

## Quick Setup (Automated)

```bash
# Run the setup wizard
python setup_wizard.py

# Or use the test script
python test_local.py
```

## Manual Setup

### 1. Database Setup

```bash
# Create database
createdb cybercafe

# Or using psql
psql -U postgres -c "CREATE DATABASE cybercafe;"
```

### 2. Environment Configuration

```bash
# Copy example env
copy .env.example .env

# Edit .env with your settings
# Minimum changes needed:
# - DATABASE_URL (if different password)
# - SECRET_KEY (generate a random one)
```

### 3. Install Dependencies

```bash
# Server dependencies
pip install -r local_server/requirements.txt

# Prisma
pip install prisma

# Dashboard
cd dashboard/frontend
npm install
cd ../..
```

### 4. Database Setup

```bash
# Generate Prisma client
prisma generate

# Push schema to database
prisma db push

# Create admin user
python scripts/create_admin.py
```

### First-time server installation

When you launch **CyberCafe Server** for the first time (or run with `--setup`), the **installation wizard** runs automatically:

1. **PostgreSQL** — host, port, credentials (creates `cybercafe` DB if missing)
2. **Café / branch** — names and optional address
3. **Admin account** — username and password for the dashboard
4. **Network** — server port and LAN URL shown for client PCs
5. **Install** — writes `.env`, applies schema, creates branch + admin

After setup, the server manager opens and can start services + dashboard.

Re-run setup anytime: **Settings → Run Setup Wizard** (stop services first), or:

```bash
cd local_server
python server_manager.py --setup
```

### 5. Start Services

**Recommended — Server Manager (API + dashboard in one app):**

```bash
scripts\start_server_manager.bat
# or: cd local_server && python server_manager.py
```

Opens a control window that starts the API, serves the built dashboard at http://localhost:8000/, and opens your browser. Use **Start** / **Stop** or the system tray.

**Development — separate terminals:**

Open **3 terminal windows**:

**Terminal 1 - Local Server:**
```bash
cd local_server
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Dashboard:**
```bash
cd dashboard/frontend
npm run dev
```

**Terminal 3 - Client (optional):**
```bash
cd client
python main.py
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Local Server API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/api/docs | Swagger UI |
| Dashboard (dev) | http://localhost:7842 | Vue dev server (`npm run dev`) |
| Dashboard (manager) | http://localhost:8000 | Bundled with server manager / installer |
| Client | Desktop app | PyQt6 lock screen |

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Super Admin |
| manager1 | manager123 | Branch Manager |

## Testing Workflow

### 1. Login to Dashboard
- Open http://localhost:7842
- Login with admin/admin123

### 2. Create a Branch
- Go to Branches page
- Add a new branch

### 3. Add PCs
- Go to PCs page
- Add test PCs with IP addresses

### 4. Generate Access Codes
- Go to Codes page
- Generate a batch of codes

### 5. Test Client
- Run the client: `cd client && python main.py`
- Enter a code to start session
- Watch timer count down

### 6. Monitor in Dashboard
- Dashboard shows real-time PC status
- Session timer updates live

## Troubleshooting

### Database Connection Error
```
Error: Connection refused
```
Solution: Ensure PostgreSQL is running on port 5432

### Port Already in Use
```
Error: [Errno 10048] Address already in use
```
Solution: Change PORT in .env or stop the other service

### Prisma Not Found
```
Error: prisma: command not found
```
Solution: `pip install prisma && prisma generate`

### Client Won't Start
```
Error: No module named 'PyQt6'
```
Solution: `pip install PyQt6`

## Testing Offline Mode

1. Stop the local server
2. Client should continue working (if previously authenticated)
3. Actions are queued in `offline_queue.json`
4. Restart server - queue syncs automatically

## Testing Real-time Updates

1. Open dashboard in browser
2. Start a session via client
3. Dashboard updates automatically via WebSocket

## Running as Windows Service

```bash
# Run as administrator
install_services.bat
```

This installs:
- CyberCafeWatchdog (client monitor)
- CyberCafeServer (server monitor)

## Performance Testing

For 50+ concurrent PCs:

```bash
# Increase UVICORN workers
uvicorn local_server.app.main:app --workers 4

# Or use gunicorn
gunicorn local_server.app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```
