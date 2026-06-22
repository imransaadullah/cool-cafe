"""Branch branding API — settings and asset uploads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from prisma import Prisma
from pydantic import BaseModel, Field

from shared.branding import (
    DEFAULT_BACKGROUND_COLOR,
    build_public_branding,
    default_logo_file_path,
    merge_branding,
)
from shared.config import settings
from shared.database import get_db

from ..auth_deps import require_roles
from ..services.branding_storage import (
    delete_asset,
    resolve_asset_path,
    save_background,
    save_logo,
)

router = APIRouter()


class BrandingBackgroundUpdate(BaseModel):
    type: Literal["color", "image"] = "color"
    color: Optional[str] = DEFAULT_BACKGROUND_COLOR
    overlay_opacity: Optional[float] = Field(default=0.45, ge=0.0, le=1.0)


class BrandingUpdate(BaseModel):
    display_name: Optional[str] = None
    tagline: Optional[str] = None
    accent_color: Optional[str] = None
    background: Optional[BrandingBackgroundUpdate] = None


async def _get_branch_or_404(branch_id: int, db: Prisma):
    branch = await db.branch.find_unique(where={"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


def _branch_config(branch) -> dict:
    return branch.config if isinstance(branch.config, dict) else {}


async def _save_branding_config(branch_id: int, branding: dict, db: Prisma):
    branch = await _get_branch_or_404(branch_id, db)
    config = _branch_config(branch)
    config["branding"] = branding
    if branding.get("display_name"):
        config["cafe_name"] = branding["display_name"]
    await db.branch.update(where={"id": branch_id}, data={"config": config})


@router.get("/branding/default/logo.png")
async def serve_default_logo():
    """Bundled platform default logo (NISS E-LIBRARY)."""
    path = default_logo_file_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Default logo not found")
    return FileResponse(path, media_type="image/png")


@router.get("/public/branding")
async def get_public_default_branding(db: Prisma = Depends(get_db)):
    """Public branding for login page (uses configured branch or first branch)."""
    branch_id = settings.BRANCH_ID
    if branch_id:
        branch = await db.branch.find_unique(where={"id": branch_id})
    else:
        branch = await db.branch.find_first(where={"isActive": True})

    if not branch:
        return build_public_branding({}, 0)

    return build_public_branding(branch.config, branch.id)


@router.get("/{branch_id}/branding")
async def get_branch_branding(branch_id: int, db: Prisma = Depends(get_db)):
    branch = await _get_branch_or_404(branch_id, db)
    return build_public_branding(branch.config, branch.id)


@router.put("/{branch_id}/branding")
async def update_branch_branding(
    branch_id: int,
    data: BrandingUpdate,
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)

    if data.display_name is not None:
        branding["display_name"] = data.display_name.strip() or branding["display_name"]
    if data.tagline is not None:
        branding["tagline"] = data.tagline.strip()
    if data.accent_color is not None:
        branding["accent_color"] = data.accent_color.strip() or branding["accent_color"]
    if data.background is not None:
        bg = branding.get("background") or {}
        bg["type"] = data.background.type
        if data.background.color is not None:
            bg["color"] = data.background.color
        if data.background.overlay_opacity is not None:
            bg["overlay_opacity"] = data.background.overlay_opacity
        if data.background.type == "color":
            bg.pop("image_path", None)
        branding["background"] = bg

    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    branch = await _get_branch_or_404(branch_id, db)
    return build_public_branding(branch.config, branch.id)


@router.post("/{branch_id}/branding/logo")
async def upload_logo(
    branch_id: int,
    file: UploadFile = File(...),
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    content = await file.read()
    try:
        _, public_path = save_logo(branch_id, file.filename or "logo.png", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)
    branding["logo_path"] = public_path
    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    return {"logo_url": public_path}


@router.post("/{branch_id}/branding/logo-client")
async def upload_client_logo(
    branch_id: int,
    file: UploadFile = File(...),
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    content = await file.read()
    try:
        _, public_path = save_logo(
            branch_id, file.filename or "logo_client.png", content, client_variant=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)
    branding["logo_client_path"] = public_path
    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    return {"logo_client_url": public_path}


@router.post("/{branch_id}/branding/background")
async def upload_background(
    branch_id: int,
    file: UploadFile = File(...),
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    content = await file.read()
    try:
        _, public_path = save_background(branch_id, file.filename or "background.jpg", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)
    bg = branding.get("background") or {}
    bg["type"] = "image"
    bg["image_path"] = public_path
    branding["background"] = bg
    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    return {"background_url": public_path}


@router.delete("/{branch_id}/branding/logo")
async def remove_logo(
    branch_id: int,
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    delete_asset(branch_id, "logo")
    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)
    branding.pop("logo_path", None)
    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    return {"message": "Logo removed"}


@router.delete("/{branch_id}/branding/logo-client")
async def remove_client_logo(
    branch_id: int,
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    delete_asset(branch_id, "logo_client")
    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)
    branding.pop("logo_client_path", None)
    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    return {"message": "Client logo removed"}


@router.delete("/{branch_id}/branding/background")
async def remove_background(
    branch_id: int,
    db: Prisma = Depends(get_db),
    _admin=Depends(require_roles("owner", "branch_admin")),
):
    delete_asset(branch_id, "background")
    branch = await _get_branch_or_404(branch_id, db)
    branding = merge_branding(branch.config)
    bg = branding.get("background") or {}
    bg["type"] = "color"
    bg.pop("image_path", None)
    branding["background"] = bg
    branding["updated_at"] = datetime.now(timezone.utc).isoformat()
    await _save_branding_config(branch_id, branding, db)
    return {"message": "Background image removed"}


@router.get("/{branch_id}/branding/assets/{filename}")
async def serve_branding_asset(branch_id: int, filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = resolve_asset_path(branch_id, filename)
    if not path:
        raise HTTPException(status_code=404, detail="Asset not found")

    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    media_type = media_types.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media_type)
