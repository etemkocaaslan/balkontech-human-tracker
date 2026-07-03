"""
ApiKeyStore — JSON-backed API key storage.

Keys are stored in API_KEYS_FILE (default: ./api_keys.json).
The actual key value is shown only once on creation; only a SHA-256 hash is stored.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


_DEFAULT_PATH = Path(os.getenv("API_KEYS_FILE", "./api_keys.json"))


@dataclass
class ApiKey:
    id: str           # uuid-like short id
    name: str         # human label, e.g. "balkontech-client"
    key_hash: str     # SHA-256 of the raw key — never stored in plain text
    created_at: str   # ISO-8601 UTC


class ApiKeyStore:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._keys: List[ApiKey] = []
        self._load()

    # ── Public ────────────────────────────────────────────────────────────────

    def create(self, name: str) -> str:
        """Create a new API key. Returns the raw key (shown only once)."""
        raw_key = "bht_" + secrets.token_hex(32)   # bht = balkontech tracker
        key_id  = secrets.token_hex(6)
        entry   = ApiKey(
            id=key_id,
            name=name.strip(),
            key_hash=self._hash(raw_key),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._keys.append(entry)
            self._save()
        return raw_key

    def list_keys(self) -> List[dict]:
        """Return all keys (without key_hash)."""
        with self._lock:
            return [
                {"id": k.id, "name": k.name, "created_at": k.created_at}
                for k in self._keys
            ]

    def delete(self, key_id: str) -> bool:
        with self._lock:
            before = len(self._keys)
            self._keys = [k for k in self._keys if k.id != key_id]
            if len(self._keys) < before:
                self._save()
                return True
            return False

    def validate(self, raw_key: str) -> bool:
        """Return True if the raw key matches any stored hash."""
        h = self._hash(raw_key)
        with self._lock:
            return any(k.key_hash == h for k in self._keys)

    def count(self) -> int:
        with self._lock:
            return len(self._keys)

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _hash(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def _load(self) -> None:
        if not self._path.exists():
            self._keys = []
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._keys = [ApiKey(**entry) for entry in data]
        except Exception:
            self._keys = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(k) for k in self._keys], indent=2),
            encoding="utf-8",
        )
