from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import settings
from shared.database import db
from .routes import auth, branches, sync, dashboard
import sys
import os

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


app = FastAPI(
    title=f"{settings.APP_NAME} - Global Server",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

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
app.include_router(branches.router, prefix="/api/branches", tags=["Branches"])
app.include_router(sync.router, prefix="/api/sync", tags=["Sync"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.on_event("startup")
async def startup_event():
    await db.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()


@app.get("/")
async def root():
    return {
        "app": f"{settings.APP_NAME} - Global Server",
        "version": settings.APP_VERSION,
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}
