"""Download and apply branch branding on the client lock screen."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from services.config_manager import client_config
from services.paths import app_path

logger = logging.getLogger(__name__)

CACHE_DIR = app_path("branding_cache")


def _cache_path(url: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    suffix = Path(urlparse(url).path).suffix.lower() or ".bin"
    return CACHE_DIR / f"{digest}{suffix}"


def _resolve_url(path_or_url: str, server_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return f"{server_url.rstrip('/')}{path_or_url}"


def fetch_pixmap(path_or_url: str, server_url: str) -> Optional[QPixmap]:
    url = _resolve_url(path_or_url, server_url)
    cache_file = _cache_path(url)

    if cache_file.is_file():
        pix = QPixmap(str(cache_file))
        if not pix.isNull():
            return pix

    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        cache_file.write_bytes(response.content)
        pix = QPixmap()
        if pix.loadFromData(QByteArray(response.content)):
            return pix
    except Exception as exc:
        logger.warning("Failed to load branding image %s: %s", url, exc)
    return None


def apply_lock_screen_branding(
    branding: Dict[str, Any],
    *,
    window_title_label: Optional[QLabel] = None,
    logo_label: Optional[QLabel] = None,
    tagline_label: Optional[QLabel] = None,
    central_widget: Optional[QWidget] = None,
    background_label: Optional[QLabel] = None,
    accent_widgets: Optional[list] = None,
) -> None:
    if not branding:
        return

    server_url = client_config.get_server_url()
    display_name = branding.get("display_name") or "Cyber Cafe"
    tagline = branding.get("tagline") or ""
    accent = branding.get("accent_color") or "#e94560"
    background = branding.get("background") or {}
    bg_type = background.get("type") or "color"
    bg_color = background.get("color") or "#1a1a2e"
    overlay = float(background.get("overlay_opacity") or 0.45)

    if window_title_label is not None:
        pass

    if logo_label is not None:
        logo_path = (
            branding.get("logo_path")
            or branding.get("logo_client_url")
            or branding.get("logo_url")
        )
        if logo_path:
            pix = fetch_pixmap(logo_path, server_url)
            if pix and not pix.isNull():
                scaled = pix.scaled(
                    320,
                    120,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logo_label.setPixmap(scaled)
                logo_label.show()
            else:
                logo_label.hide()
        else:
            logo_label.hide()

    if tagline_label is not None:
        if tagline:
            tagline_label.setText(tagline)
            tagline_label.show()
        else:
            tagline_label.hide()

    if central_widget is not None:
        if bg_type == "image" and (
            background.get("image_path") or background.get("image_url")
        ):
            image_ref = background.get("image_path") or background.get("image_url")
            pix = fetch_pixmap(image_ref, server_url)
            if pix and not pix.isNull() and background_label is not None:
                background_label.setPixmap(
                    pix.scaled(
                        central_widget.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                background_label.setGeometry(central_widget.rect())
                background_label.lower()
                background_label.show()
                rgba = _hex_to_rgba(bg_color, overlay)
                central_widget.setStyleSheet(
                    f"#lockScreenCentral {{ background-color: {rgba}; }}"
                )
            else:
                if background_label is not None:
                    background_label.hide()
                central_widget.setStyleSheet(
                    f"#lockScreenCentral {{ background-color: {bg_color}; }}"
                )
        else:
            if background_label is not None:
                background_label.hide()
            central_widget.setStyleSheet(
                f"#lockScreenCentral {{ background-color: {bg_color}; }}"
            )

    for widget in accent_widgets or []:
        if hasattr(widget, "setStyleSheet"):
            widget.setStyleSheet(f"color: {accent}; background: transparent;")


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        return f"rgba(26, 26, 46, {alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
