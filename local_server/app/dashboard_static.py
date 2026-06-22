"""Serve the built Vue dashboard from the FastAPI app (production installs)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def find_dashboard_dist() -> Path | None:
    """Locate dashboard/frontend/dist for dev or PyInstaller bundles."""
    candidates: list[Path] = []

    env_path = os.environ.get("DASHBOARD_DIST")
    if env_path:
        candidates.append(Path(env_path))

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "dashboard" / "dist")
        candidates.append(exe_dir / "dashboard" / "dist")

    candidates.append(_repo_root() / "dashboard" / "frontend" / "dist")

    for path in candidates:
        index = path / "index.html"
        if index.is_file():
            return path
    return None


def mount_dashboard(app: FastAPI) -> bool:
    """Mount SPA static assets. Returns True if dashboard files were found."""
    dist = find_dashboard_dist()
    if not dist:
        return False

    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="dashboard-assets")

    index_path = dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def dashboard_root():
        return FileResponse(index_path)

    @app.get("/login", include_in_schema=False)
    async def dashboard_login():
        return FileResponse(index_path)

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def dashboard_spa(spa_path: str):
        if spa_path.startswith("api/") or spa_path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        if spa_path.startswith("ws"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = dist / spa_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_path)

    return True
