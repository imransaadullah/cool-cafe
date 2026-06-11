# CyberCafe Management System

A comprehensive cyber cafe management system with support for multiple branches, offline operation, and detailed reporting.

## Features

- **Session Management**: Start, pause, resume, and stop sessions
- **Code System**: Generate and print access codes for users
- **Real-time Dashboard**: Monitor all PCs and sessions via WebSocket
- **Offline Resilience**: Continue working without internet
- **Multi-branch Support**: Manage multiple locations
- **Content Filtering**: DNS, process, and URL filtering
- **Revenue Reports**: Detailed financial reporting
- **Payment Integration**: KongaPay and Paystack support
- **Windows Service**: Watchdog service for client monitoring

## Tech Stack

- **Backend**: Python, FastAPI, Prisma ORM
- **Database**: PostgreSQL
- **Frontend**: Vue.js 3, Tailwind CSS
- **Client**: PyQt6, PyInstaller
- **Real-time**: WebSocket

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and setup
git clone <repository>
cd cyber-cafe

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Start all services
cd deploy/docker
docker-compose up -d

# Access dashboard
open http://localhost:3000
```

### Option 2: Manual Setup

```bash
# 1. Install Python dependencies
pip install -r local_server/requirements.txt

# 2. Install Prisma
pip install prisma

# 3. Generate Prisma client
prisma generate

# 4. Setup database
prisma db push

# 5. Create admin user
python scripts/create_admin.py

# 6. Start local server
uvicorn local_server.app.main:app --reload

# 7. Start dashboard
cd dashboard/frontend
npm install
npm run dev
```

## Project Structure

```
cyber-cafe/
├── prisma/
│   └── schema.prisma          # Database schema
├── shared/                    # Common code
│   ├── config.py
│   ├── database.py
│   └── utils/
├── local_server/              # Local cafe server
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   └── websocket.py
│   └── requirements.txt
├── global_server/             # Central sync server
│   ├── app/
│   └── requirements.txt
├── client/                    # PyQt6 desktop client
│   ├── main.py
│   ├── ui/
│   ├── services/
│   └── build.spec
├── dashboard/frontend/        # Vue.js admin dashboard
│   ├── src/
│   └── package.json
├── deploy/                    # Deployment configs
│   ├── docker/
│   └── bare_metal/
├── scripts/
│   └── create_admin.py
├── docs/
│   └── api.md
└── .env.example
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

See [docs/api.md](docs/api.md) for detailed API documentation.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://postgres:postgres@localhost:5432/cybercafe |
| SECRET_KEY | JWT secret key | (generated) |
| DEPLOYMENT_MODE | local_only, hybrid, global_only | local_only |
| HOST | Server host | 0.0.0.0 |
| PORT | Server port | 8000 |
| CORS_ORIGINS | Allowed origins | ["http://localhost:3000"] |
| PAYSTACK_SECRET_KEY | Paystack secret key | - |
| PAYSTACK_PUBLIC_KEY | Paystack public key | - |
| KONGA_PAY_MERCHANT_ID | KongaPay merchant ID | - |

## Deployment

### Docker

```bash
cd deploy/docker
docker-compose up -d
```

### Bare Metal (Linux)

```bash
cd deploy/bare_metal
sudo ./install.sh
```

### Windows Client

1. Build the client:
```bash
cd client
pip install -r requirements.txt
pyinstaller build.spec
```

2. Install the watchdog service (as Administrator):
```bash
cd client/services
install_watchdog.bat
```

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r local_server/requirements.txt

# Generate Prisma client
prisma generate

# Setup database
prisma db push

# Start development server
uvicorn local_server.app.main:app --reload
```

### Dashboard Development

```bash
cd dashboard/frontend
npm install
npm run dev
```

## License

MIT License
