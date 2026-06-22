# Local Testing Guide

Test the full CyberCafe stack on a single Windows PC (or laptop acting as server + one client).

See also: [README](../README.md) · [Distribution guide](../deploy/DISTRIBUTION.md)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **PostgreSQL** | https://www.postgresql.org/download/windows/ |
| **Python 3.11+** | python.org or Microsoft Store |
| **Node.js 18+** | For dashboard dev server |
| **Git** | To clone the repo |

---

## Fastest path: `start_test.bat`

From the repo root:

```bat
copy .env.example .env
start_test.bat
```

This script:

1. Runs `setup.py` (dependencies, admin seed, dashboard `npm install`)
2. Syncs Prisma schema and client (`setup.py --prisma-only`)
3. Starts the local API (`scripts\start_server.bat`)
4. Waits for http://localhost:8000/api/health
5. Starts the dashboard dev server (`scripts\start_dashboard.bat`)
6. Optionally launches the client on the same machine

### Access points after `start_test.bat`

| Service | URL |
|---------|-----|
| Local server API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/api/docs |
| Dashboard (dev) | http://localhost:7842 |
| Health check | http://localhost:8000/api/health |

### Default login

| Username | Password |
|----------|----------|
| `admin` | `admin123` |

(Set by `setup.py` / `scripts\create_admin.py` / seed — change after first login in production.)

---

## Alternative: Server Manager (production-like GUI)

Runs API + **embedded** dashboard on port 8000 in one desktop app:

```bat
scripts\start_server_manager.bat
```

On first launch (or with `--setup`), the **installation wizard** collects:

1. PostgreSQL connection
2. Café / branch name
3. Admin account
4. Network port and client URL hint
5. Schema push and branch creation

Re-run setup: **Settings → Run Setup Wizard** in the manager, or:

```bat
cd local_server
python server_manager.py --setup
```

| Mode | Dashboard URL |
|------|----------------|
| Dev (`start_test.bat`) | http://localhost:7842 |
| Server manager / installed build | http://localhost:8000 |

---

## Manual setup (step by step)

Use this if you prefer separate control or `start_test.bat` fails.

### 1. Database

```bat
psql -U postgres -c "CREATE DATABASE cybercafe;"
```

### 2. Environment

```bat
copy .env.example .env
```

Edit `.env` — at minimum set `DATABASE_URL` and a strong `SECRET_KEY`.

### 3. Dependencies

```bat
pip install -r local_server\requirements.txt
pip install prisma
cd dashboard\frontend && npm install && cd ..\..
```

### 4. Prisma

```bat
python scripts\prisma_generate.py
prisma db push
python scripts\create_admin.py
```

> **Windows Store Python:** use `python scripts\prisma_generate.py` instead of bare `prisma generate`.

### 5. Start services (three terminals)

**Terminal 1 — API:**

```bat
scripts\start_server.bat
```

**Terminal 2 — Dashboard:**

```bat
scripts\start_dashboard.bat
```

**Terminal 3 — Client (optional):**

```bat
client\start_client.bat
```

Or for debugging with console output:

```bat
cd client
python main.py --dev
```

---

## Testing workflow

### 1. Login to dashboard

Open http://localhost:7842 → login `admin` / `admin123`

### 2. Branding (optional)

Go to **Branding** → set display name, colors, upload logo → Save.  
Launch client to see lock screen branding after the next config sync.

### 3. Register a PC (via client setup)

Run the client. First launch opens the **setup wizard**:

- Server URL: `http://localhost:8000` (same PC) or `http://<LAN-IP>:8000` (other PCs)
- PC name / number / branch ID
- Security codes (static master + recovery combo)

Or register from dashboard **PCs** page.

### 4. Sell or generate access codes

- **Codes** → generate a batch, or
- Counter sell-time flow in the dashboard

Codes are **8 alphanumeric characters** (e.g. `AB12CD34`). Dashes are optional.

### 5. Start a session on the client

Enter the access code on the lock screen → session overlay shows the timer.

### 6. Monitor live

- **Dashboard** home — PC floor map updates via WebSocket
- Pause / extend / force logout from **PCs** or **Sessions**

---

## Client commands

| Command | Purpose |
|---------|---------|
| `client\start_client.bat` | Launch without terminal |
| `python client\main.py` | Debug (console) |
| `python client\main.py --dev` | Relaxed kiosk (can exit with Esc) |
| `client\reset_client.bat` | Factory reset |
| `python client\main.py --reset --yes` | Reset without prompts |

**Exit setup wizard:** use **Exit Setup** — setup is not kiosk-locked.

---

## Testing security

| Test | How |
|------|-----|
| Wrong access code | Enter invalid code 3× → alarm screen |
| Recovery combo | Hold Alt + keys shown on alarm (from setup step 3) |
| Staff master code | **Staff** button on lock screen |
| Production lock | Default mode blocks Alt+F4 / Esc until staff unlock |

---

## Testing offline behavior

1. Start a session on the client
2. Stop the local server
3. Client locks after heartbeat grace period
4. Events queue to `client/offline_queue.json`
5. Restart server — client reconnects on next heartbeat

---

## Testing the unified installer (optional)

```bat
scripts\build_installer.bat
```

Output: `deploy\installer\installer_output\CyberCafe Setup.exe`

Preview UI without full build (after payloads staged):

```bat
scripts\start_installer.bat
```

See [deploy/DISTRIBUTION.md](../deploy/DISTRIBUTION.md).

---

## Troubleshooting

### Database connection refused

PostgreSQL is not running or `DATABASE_URL` is wrong. Start the service and verify credentials.

### Port already in use (8000 or 7842)

Change `PORT` in `.env` or stop the conflicting process:

```bat
netstat -ano | findstr :8000
```

### `prisma: command not found`

```bat
python scripts\prisma_generate.py
```

### `No module named 'PyQt6'`

```bat
pip install PyQt6
```

### Client can't reach server from another PC

Use the server's **LAN IP**, not `localhost`:

```
http://192.168.x.x:8000
```

Ensure Windows Firewall allows inbound TCP on port 8000.

### Access code always invalid

- Confirm code exists and is active in dashboard **Codes**
- Use the exact 8-character code (case insensitive)
- Check client `pc_id` matches registration

### Dashboard shows old branding

Hard-refresh the browser. Client branding updates on heartbeat config push.

### `start_test.bat` fails at setup

Run `python setup.py` alone and read the error. Common fixes: PostgreSQL down, missing npm, wrong `DATABASE_URL`.

---

## Performance notes

For many concurrent clients on one server machine, run multiple Uvicorn workers:

```bat
uvicorn local_server.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Tune `heartbeat_interval` in client config (default 5–30s) to balance load vs. responsiveness.
