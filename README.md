# CyberCafe Management System

A white-label cyber café platform for session management, PC floor control, access codes, security, and multi-branch operations. One codebase ships three roles: **Local Server** (branch), **Global Server** (multi-site owner hub), and **Client** (gaming PC kiosk).

---

## Choose your path

| I want to… | Start here |
|------------|------------|
| **Develop / test on one PC** | [Local testing guide](docs/LOCAL_TESTING.md) → run `start_test.bat` |
| **Ship installers to customers** | [Distribution guide](deploy/DISTRIBUTION.md) → `scripts\build_installer.bat` |
| **API reference** | [docs/api.md](docs/api.md) and http://localhost:8000/api/docs |
| **Configure branding (logo, colors)** | Dashboard → **Branding** (`/branding`) after server is running |
| **Multi-site / owner hub** | Install **Global Server** — see [Multi-site deployment](#multi-site-deployment) |

---

## Architecture

```
                    ┌─────────────────────┐
                    │   Global Server     │  optional — HQ / cloud
                    │   (owner API, sync) │
                    └──────────┬──────────┘
                               │ GLOBAL_SERVER_URL
         ┌─────────────────────┴─────────────────────┐
         │           Local Server (per branch)      │
         │  FastAPI · PostgreSQL · Vue dashboard    │
         └─────────────────────┬─────────────────────┘
                               │ LAN http://<server-ip>:8000
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         Client PC 1       Client PC 2       Client PC N
         (lock screen)     (lock screen)     (lock screen)
```

| Component | Purpose | Default install folder (Windows) |
|-----------|---------|----------------------------------|
| **Local Server** | Branch API, admin dashboard, codes, sessions, reports | `C:\Program Files\CyberCafe Local Server` |
| **Global Server** | Multi-branch sync and owner reporting | `C:\Program Files\CyberCafe Global Server` |
| **Client** | Full-screen kiosk, access codes, watchdog | `C:\Program Files\CyberCafe Client` |

---

## Quick start (developers)

**Prerequisites:** PostgreSQL, Python 3.11+, Node.js 18+

```bat
git clone https://github.com/imransaadullah/cool-cafe.git
cd cool-cafe
copy .env.example .env
start_test.bat
```

`start_test.bat` runs setup, syncs Prisma, starts the API and dashboard, and optionally launches the client.

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Dashboard (dev) | http://localhost:7842 |
| API docs | http://localhost:8000/api/docs |
| Login | `admin` / `admin123` (after seed) |

Full details: [docs/LOCAL_TESTING.md](docs/LOCAL_TESTING.md)

---

## Quick start (operators / installers)

Build one graphical installer that bundles all three roles:

```bat
scripts\build_installer.bat
```

Output: `deploy\installer\installer_output\CyberCafe Setup.exe`

Give customers that single file. They pick **Local Server**, **Global Server**, or **Client** during setup. Each role runs a **first-run wizard** (database, admin, network, PC registration).

Full details: [deploy/DISTRIBUTION.md](deploy/DISTRIBUTION.md)

---

## Features

- **Sessions** — Start, pause, resume, logout; server-authoritative timers
- **Access codes** — Generate, sell at counter, print; 8-character tickets
- **Live floor map** — PC status and sessions via WebSocket
- **Security** — Master codes, recovery key combos, alarms, audit log
- **Content filtering** — DNS, URL, and process blocking (per branch / PC)
- **Revenue & reports** — Payments and reporting in the dashboard
- **White-label branding** — Per-branch name, logo, accent color, background (dashboard + client lock screen)
- **Kiosk client** — Production lock mode, watchdog, autostart
- **Multi-branch** — Optional global server and sync worker
- **Offline resilience** — Client queues events when server is unreachable

---

## Branding (white-label)

Each branch can customize how the product looks without rebuilding installers:

1. Open dashboard → **Branding**
2. Set **display name**, **tagline**, **accent color**, **background** (color or image)
3. Upload **dashboard logo** and optional **client lock screen logo**
4. Save — gaming PCs pick up changes on the next heartbeat (~30s)

Assets are stored on the local server under `local_server/data/branding/{branch_id}/`.

---

## Security overview

| Mechanism | Used for |
|-----------|----------|
| **Access code** | Customer session ticket (from Codes / counter sell) |
| **Master code** | Staff maintenance unlock on client (Staff button) |
| **Recovery combo** | `Alt` + configured keys — dismiss alarm or unlock kiosk |
| **Production mode** | Blocks customer exit; staff unlock required |

**Client dev flags:**

```bat
cd client
python main.py --dev          rem relaxed kiosk for debugging
python main.py --reset --yes  rem factory reset
client\reset_client.bat       rem same, with prompts
```

**Re-run server setup:**

```bat
scripts\start_server_manager.bat
rem Or: "CyberCafe Server.exe" --setup
```

---

## Multi-site deployment

1. Install **Global Server** at HQ (optional)
2. Install **Local Server** at each café branch (PostgreSQL on each branch server)
3. Install **Client** on every gaming PC
4. During local server setup, set `GLOBAL_SERVER_URL` in `.env` if using sync

Local server runs a background sync worker when `GLOBAL_SERVER_URL` is configured.

---

## Project structure

```
cool-cafe/
├── prisma/schema.prisma       # Database schema
├── shared/                    # Config, branding, auth, app policy
├── local_server/              # Branch API + server manager + setup wizard
├── global_server/             # Owner hub API + server manager
├── client/                    # PyQt6 kiosk client
├── dashboard/frontend/        # Vue 3 admin UI
├── installer/                 # PyQt unified graphical installer
├── scripts/                   # Build, Prisma, start helpers
├── deploy/
│   ├── DISTRIBUTION.md        # Shipping guide
│   ├── installer/             # Inno scripts (legacy) + payload staging
│   └── docker/                # Optional container deployment
└── docs/
    ├── LOCAL_TESTING.md
    └── api.md
```

---

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://postgres:postgres@localhost:5432/cybercafe` |
| `SECRET_KEY` | JWT signing key | change in production |
| `HOST` / `PORT` | API bind address | `0.0.0.0` / `8000` |
| `DEPLOYMENT_MODE` | `local_only`, `hybrid`, `global_only` | `local_only` |
| `GLOBAL_SERVER_URL` | Owner hub URL for sync | empty |
| `BRANCH_ID` | Default branch | `1` |
| `CORS_ORIGINS` | Dashboard origins | includes `http://localhost:7842` |

**Prisma on Windows** (if `prisma` is not on PATH):

```bat
python scripts\prisma_generate.py
```

---

## Development commands

| Task | Command |
|------|---------|
| Full dev stack | `start_test.bat` |
| Server manager (GUI) | `scripts\start_server_manager.bat` |
| API only | `scripts\start_server.bat` |
| Dashboard dev server | `scripts\start_dashboard.bat` |
| Client | `client\start_client.bat` or `python client\main.py` |
| Build unified installer | `scripts\build_installer.bat` |
| Preview installer UI | `scripts\start_installer.bat` |
| Seed admin | `python scripts\create_admin.py` |

### Manual API + dashboard (without `start_test.bat`)

```bat
pip install -r local_server\requirements.txt
python scripts\prisma_generate.py
prisma db push
python scripts\create_admin.py
scripts\start_server.bat
scripts\start_dashboard.bat
```

### Docker (optional)

```bash
cd deploy/docker
docker-compose up -d
```

Dashboard: http://localhost:7842

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Server won't start | Check PostgreSQL is running; verify `DATABASE_URL` in `.env` |
| `prisma` not found | `python scripts\prisma_generate.py` |
| Port 8000 in use | Change `PORT` in `.env` or stop the other process |
| Client can't connect | Use LAN IP, not `localhost`, from other PCs: `http://<server-ip>:8000` |
| Access code rejected | Codes are 8 characters; dashes/spaces are stripped automatically |
| Recovery combo ignored | Hold **Alt** and press all keys together (shown on alarm screen) |
| Can't exit client setup | Use **Exit Setup** or window close — setup is not kiosk-locked |
| Installer Next disabled | Pick a role on the installation type page (fixed in latest build) |
| Branding not on client | Wait for heartbeat or restart client; check **Branding** page saved |

More: [docs/LOCAL_TESTING.md#troubleshooting](docs/LOCAL_TESTING.md#troubleshooting)

---

## API documentation

- Swagger: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Markdown: [docs/api.md](docs/api.md)

---

## Tech stack

- **Backend:** Python, FastAPI, Prisma ORM, PostgreSQL
- **Dashboard:** Vue 3, Tailwind CSS, Pinia
- **Client / installers:** PyQt6, PyInstaller
- **Real-time:** WebSocket

---

## License

MIT License
