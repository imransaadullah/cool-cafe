"""Store branch branding asset files on disk."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Tuple

from shared.branding import ASSET_FILES

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_LOGO_BYTES = 512 * 1024
MAX_BACKGROUND_BYTES = 2 * 1024 * 1024

_REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDING_ROOT = _REPO_ROOT / "local_server" / "data" / "branding"


def branch_assets_dir(branch_id: int) -> Path:
    path = BRANDING_ROOT / str(branch_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset_file_path(branch_id: int, filename: str) -> Path:
    return branch_assets_dir(branch_id) / filename


def resolve_asset_path(branch_id: int, filename: str) -> Optional[Path]:
    path = asset_file_path(branch_id, filename)
    if path.is_file():
        return path
    return None


def _validate_upload(filename: str, content: bytes, max_bytes: int) -> Tuple[bool, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        return False, "Unsupported image type. Use PNG, JPG, WEBP, or GIF."
    if len(content) > max_bytes:
        return False, f"File too large (max {max_bytes // 1024} KB)."
    if not content:
        return False, "Empty file."
    return True, ""


def save_logo(branch_id: int, filename: str, content: bytes, *, client_variant: bool = False) -> Tuple[str, str]:
    ok, msg = _validate_upload(filename, content, MAX_LOGO_BYTES)
    if not ok:
        raise ValueError(msg)

    ext = Path(filename).suffix.lower() or ".png"
    target_name = ASSET_FILES["logo_client" if client_variant else "logo"]
    if ext != Path(target_name).suffix:
        target_name = f"{Path(target_name).stem}{ext}"

    dest = asset_file_path(branch_id, target_name)
    dest.write_bytes(content)
    return target_name, f"/api/branches/{branch_id}/branding/assets/{target_name}"


def save_background(branch_id: int, filename: str, content: bytes) -> Tuple[str, str]:
    ok, msg = _validate_upload(filename, content, MAX_BACKGROUND_BYTES)
    if not ok:
        raise ValueError(msg)

    ext = Path(filename).suffix.lower() or ".jpg"
    target_name = ASSET_FILES["background"]
    if ext != Path(target_name).suffix:
        target_name = f"{Path(target_name).stem}{ext}"

    dest = asset_file_path(branch_id, target_name)
    dest.write_bytes(content)
    return target_name, f"/api/branches/{branch_id}/branding/assets/{target_name}"


def delete_asset(branch_id: int, asset_key: str) -> None:
    filename = ASSET_FILES.get(asset_key)
    if not filename:
        return
    path = asset_file_path(branch_id, filename)
    if path.is_file():
        path.unlink()

    # Also remove alternate extensions if present
    stem = Path(filename).stem
    assets_dir = branch_assets_dir(branch_id)
    for candidate in assets_dir.glob(f"{stem}.*"):
        if candidate.is_file():
            candidate.unlink()


def clear_branch_assets(branch_id: int) -> None:
    assets_dir = branch_assets_dir(branch_id)
    if assets_dir.is_dir():
        shutil.rmtree(assets_dir, ignore_errors=True)
