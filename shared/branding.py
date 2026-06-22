"""Branch branding defaults and merge helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_DISPLAY_NAME = "NISS E-LIBRARY"
DEFAULT_TAGLINE = ""
DEFAULT_ACCENT_COLOR = "#1B7F3A"
DEFAULT_BACKGROUND_COLOR = "#0f1a14"
DEFAULT_LOGO_API_PATH = "/api/branches/branding/default/logo.png"

DEFAULT_BRANDING: Dict[str, Any] = {
    "display_name": DEFAULT_DISPLAY_NAME,
    "tagline": DEFAULT_TAGLINE,
    "accent_color": DEFAULT_ACCENT_COLOR,
    "background": {
        "type": "color",
        "color": DEFAULT_BACKGROUND_COLOR,
        "image_path": None,
        "overlay_opacity": 0.45,
    },
    "logo_path": None,
    "logo_client_path": None,
    "updated_at": None,
}

ASSET_FILES = {
    "logo": "logo.png",
    "logo_client": "logo_client.png",
    "background": "background.jpg",
}


def default_logo_file_path() -> Path:
    """Bundled NISS logo shipped with the platform."""
    return Path(__file__).resolve().parent / "assets" / "branding" / "niss_logo.png"


def default_branding_seed() -> Dict[str, Any]:
    """Branding dict for new branch setup (custom uploads still override later)."""
    return deepcopy(DEFAULT_BRANDING)


def resolve_logo_url(branding: Dict[str, Any]) -> str:
    return (
        branding.get("logo_path")
        or branding.get("logo_client_path")
        or DEFAULT_LOGO_API_PATH
    )


def resolve_logo_client_url(branding: Dict[str, Any]) -> str:
    return (
        branding.get("logo_client_path")
        or branding.get("logo_path")
        or DEFAULT_LOGO_API_PATH
    )


def _merge_dict(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def get_branch_config_dict(branch_config: Any) -> dict:
    if isinstance(branch_config, dict):
        return branch_config
    return {}


def get_raw_branding(branch_config: Any) -> dict:
    config = get_branch_config_dict(branch_config)
    raw = config.get("branding")
    if isinstance(raw, dict):
        return raw
    cafe_name = config.get("cafe_name")
    if cafe_name:
        return {"display_name": str(cafe_name)}
    return {}


def merge_branding(branch_config: Any) -> Dict[str, Any]:
    raw = get_raw_branding(branch_config)
    branding = _merge_dict(DEFAULT_BRANDING, raw)
    display = branding.get("display_name") or get_branch_config_dict(branch_config).get(
        "cafe_name"
    )
    if display:
        branding["display_name"] = str(display)
    return branding


def asset_url(branch_id: int, asset_key: str) -> Optional[str]:
    filename = ASSET_FILES.get(asset_key)
    if not filename:
        return None
    return f"/api/branches/{branch_id}/branding/assets/{filename}"


def build_client_branding(branch_config: Any, branch_id: int) -> Dict[str, Any]:
    """Branding payload pushed to gaming clients (relative asset paths)."""
    branding = merge_branding(branch_config)
    background = branding.get("background") or {}
    bg_type = background.get("type") or "color"

    payload: Dict[str, Any] = {
        "display_name": branding.get("display_name", DEFAULT_DISPLAY_NAME),
        "tagline": branding.get("tagline") or "",
        "accent_color": branding.get("accent_color") or DEFAULT_ACCENT_COLOR,
        "background": {
            "type": bg_type,
            "color": background.get("color") or DEFAULT_BACKGROUND_COLOR,
            "overlay_opacity": background.get(
                "overlay_opacity", DEFAULT_BRANDING["background"]["overlay_opacity"]
            ),
        },
        "logo_path": resolve_logo_client_url(branding),
    }

    bg = branding.get("background") or {}
    if (bg.get("type") or "color") == "image" and bg.get("image_path"):
        payload["background"]["image_path"] = bg["image_path"]

    return payload


def build_public_branding(branch_config: Any, branch_id: int) -> Dict[str, Any]:
    """Branding payload for dashboard (includes public asset URLs)."""
    branding = merge_branding(branch_config)
    background = dict(branding.get("background") or DEFAULT_BRANDING["background"])

    if background.get("type") == "image" and background.get("image_path"):
        background["image_url"] = background["image_path"]
    else:
        background["image_url"] = None

    return {
        "display_name": branding.get("display_name", DEFAULT_DISPLAY_NAME),
        "tagline": branding.get("tagline") or "",
        "accent_color": branding.get("accent_color") or DEFAULT_ACCENT_COLOR,
        "background": background,
        "logo_url": resolve_logo_url(branding),
        "logo_client_url": resolve_logo_client_url(branding),
        "updated_at": branding.get("updated_at"),
    }
