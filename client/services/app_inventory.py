"""Upload scanned app inventory from the client."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from services.app_scanner import scan_installed_apps
from services.config_manager import client_config

logger = logging.getLogger(__name__)


def scan_and_upload(pc_id: int | None = None) -> bool:
    server_url = client_config.get_server_url()
    pc_id = pc_id or client_config.get_pc_id()

    try:
        apps: List[Dict[str, Any]] = scan_installed_apps()
        response = requests.post(
            f"{server_url}/api/pcs/{pc_id}/apps/inventory",
            json={
                "apps": apps,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
            },
            timeout=30,
        )
        if response.status_code == 200:
            logger.info("Uploaded %s apps for PC %s", len(apps), pc_id)
            return True
        logger.warning("App inventory upload failed: %s", response.status_code)
    except requests.exceptions.RequestException as exc:
        logger.warning("App inventory upload error: %s", exc)
    return False
