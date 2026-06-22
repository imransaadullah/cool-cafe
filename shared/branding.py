"""Branch branding defaults and merge helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

DEFAULT_BRANDING: Dict[str, Any] = {
    "display_name": "Cyber Cafe",
    "tagline": "",
    "accent_color": "#e94560",
    "background": {
        "type": "color",
        "color": "#1a1a2e",
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
        "display_name": branding.get("display_name", DEFAULT_BRANDING["display_name"]),
        "tagline": branding.get("tagline") or "",
        "accent_color": branding.get("accent_color") or DEFAULT_BRANDING["accent_color"],
        "background": {
            "type": bg_type,
            "color": background.get("color") or DEFAULT_BRANDING["background"]["color"],
            "overlay_opacity": background.get(
                "overlay_opacity", DEFAULT_BRANDING["background"]["overlay_opacity"]
            ),
        },
    }

    logo_path = branding.get("logo_client_path") or branding.get("logo_path")
    if logo_path:
        payload["logo_path"] = logo_path

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

    logo_url = branding.get("logo_path")
    logo_client_url = branding.get("logo_client_path") or logo_url

    return {
        "display_name": branding.get("display_name", DEFAULT_BRANDING["display_name"]),
        "tagline": branding.get("tagline") or "",
        "accent_color": branding.get("accent_color") or DEFAULT_BRANDING["accent_color"],
        "background": background,
        "logo_url": logo_url,
        "logo_client_url": logo_client_url,
        "updated_at": branding.get("updated_at"),
    }
