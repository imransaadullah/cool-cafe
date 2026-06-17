from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from shared.config import settings
from shared.database import db
from .routes import auth, pcs, sessions, codes, dashboard, filter_rules, payments, content_filter, webhooks, master_codes, branches, security
from .websocket import websocket_endpoint, manager
from .middleware import ErrorHandlerMiddleware, RequestLoggingMiddleware, AdminAuthMiddleware
from .services.sync_worker import start_sync_worker, stop_sync_worker
from .services.audit import audit_logger
import sys
import os
import logging

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add middleware (order matters - last added is first executed)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AdminAuthMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(pcs.router, prefix="/api/pcs", tags=["PCs"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(codes.router, prefix="/api/codes", tags=["Codes"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(filter_rules.router, prefix="/api/filters", tags=["Filter Rules"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(content_filter.router, prefix="/api/content-filter", tags=["Content Filter"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(master_codes.router, prefix="/api/master-codes", tags=["Master Codes"])
app.include_router(branches.router, prefix="/api/branches", tags=["Branches"])
app.include_router(security.router, prefix="/api/security", tags=["Security"])


@app.on_event("startup")
async def startup_event():
    logger.info("Starting local server...")
    await db.connect()
    audit_logger.connect(db.client)
    start_sync_worker(db)
    logger.info("Database connected")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down local server...")
    stop_sync_worker()
    await db.disconnect()
    logger.info("Database disconnected")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mode": settings.DEPLOYMENT_MODE,
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)
