"""
DashboardAPIClient — isolated API communicator for the Master Dashboard.

Communicates with the balkontech-server REST API under /api/v1/ prefix.
Reads settings (Base URL, X-API-Key) from the shared QSettings registry.
Methods are designed to be called safely from QThreads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx
from PyQt6.QtCore import QSettings

APP_ORG = "Balkontech"
APP_NAME = "HumanTracker"


class DashboardAPIClient:
    """Client for Balkontech Server APIs.

    Acts as the single source of truth for the dashboard.
    """

    def __init__(self) -> None:
        self.reload_settings()

    def reload_settings(self) -> None:
        """Reads configuration from QSettings."""
        settings = QSettings(APP_ORG, APP_NAME)
        self.base_url = settings.value("api/base_url", "http://127.0.0.1:8000").rstrip("/")
        self.api_key = settings.value("api/key", "")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    # ── Health Poll ───────────────────────────────────────────────────────────

    def check_health(self) -> bool:
        """Hits the server /health endpoint to check reachability."""
        try:
            url = f"{self.base_url}/health"
            r = httpx.get(url, headers=self._headers(), timeout=2.0)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except Exception:
            return False

    # ── Models (via /api/v1/models) ───────────────────────────────────────────

    def get_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from the server.

        Returns a list of dictionaries with model information.
        """
        url = f"{self.base_url}/api/v1/models"
        try:
            r = httpx.get(url, headers=self._headers(), timeout=5.0)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch models: {exc}")

    # ── Sessions (via /api/v1/sessions) ───────────────────────────────────────

    def get_sessions(self) -> List[str]:
        """Fetch list of active session IDs."""
        url = f"{self.base_url}/api/v1/sessions"
        try:
            r = httpx.get(url, headers=self._headers(), timeout=5.0)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch sessions: {exc}")

    def get_session_detail(self, session_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific session."""
        url = f"{self.base_url}/api/v1/sessions/{session_id}"
        try:
            r = httpx.get(url, headers=self._headers(), timeout=5.0)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch details for session {session_id[:8]}: {exc}")

    def delete_session(self, session_id: str) -> bool:
        """Deletes/stops a tracking session on the server."""
        url = f"{self.base_url}/api/v1/sessions/{session_id}"
        try:
            r = httpx.delete(url, headers=self._headers(), timeout=5.0)
            return r.status_code == 204
        except Exception as exc:
            raise RuntimeError(f"Failed to delete session {session_id[:8]}: {exc}")
