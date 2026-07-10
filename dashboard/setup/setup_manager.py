"""
SetupManager — bootstrap logic for the Balkontech Master Dashboard.

Responsibilities:
  1. Create / reuse a Python venv named 'fwa' at the repo root.
  2. Install server + client requirements into it (idempotent).
  3. Download missing YOLO detector models from HuggingFace.

All operations are designed to be run inside a QThread so the UI
remains responsive while setup is in progress.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

_REPO_ROOT    = Path(__file__).resolve().parent.parent.parent
_VENV_DIR     = _REPO_ROOT / "fwa"
_SERVER_DIR   = _REPO_ROOT / "balkontech-server"
_CLIENT_DIR   = _REPO_ROOT / "balkontech-client"
_DETECTORS    = _SERVER_DIR / "models" / "detectors"

# Python executable inside the venv
if sys.platform == "win32":
    VENV_PYTHON = _VENV_DIR / "Scripts" / "python.exe"
else:
    VENV_PYTHON = _VENV_DIR / "bin" / "python"

# HuggingFace repo and model filenames to download
HF_REPO_ID = "etemkocaaslan/balkontech-models"
HF_MODELS  = ["yolo11x_best.pt", "yolo26x_best.pt"]

# Merged requirements to install into venv
REQUIREMENTS = [
    _SERVER_DIR / "requirements.txt",
    _CLIENT_DIR / "requirements.txt",
    _REPO_ROOT  / "dashboard" / "requirements.txt",
]

# ── Logging callback type ─────────────────────────────────────────────────────

LogFn = Callable[[str], None]


# ── Step implementations ──────────────────────────────────────────────────────

def venv_exists() -> bool:
    """Return True if the fwa venv Python binary exists."""
    return VENV_PYTHON.exists()


def create_venv(log: LogFn) -> None:
    """Create the fwa venv if it doesn't already exist."""
    if venv_exists():
        log(f"[Setup] venv already exists at: {_VENV_DIR}\n")
        return
    log(f"[Setup] Creating venv at: {_VENV_DIR} ...\n")
    subprocess.run(
        [sys.executable, "-m", "venv", str(_VENV_DIR)],
        check=True,
    )
    log("[Setup] venv created.\n")


def install_requirements(log: LogFn) -> None:
    """Install all requirements into the venv (skips already-installed)."""
    pip = str(VENV_PYTHON.with_name("pip") if sys.platform != "win32"
              else VENV_PYTHON.parent / "pip.exe")

    # upgrade pip first
    log("[Setup] Upgrading pip...\n")
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )

    for req_file in REQUIREMENTS:
        if not req_file.exists():
            log(f"[Setup] Skipping missing requirements file: {req_file.name}\n")
            continue
        log(f"[Setup] Installing {req_file.name} ...\n")
        subprocess.run(
            [
                str(VENV_PYTHON), "-m", "pip", "install",
                "-r", str(req_file),
            ],
            check=True,
        )
    log("[Setup] All packages installed.\n")


def missing_models() -> List[str]:
    """Return list of model filenames that are not yet downloaded."""
    _DETECTORS.mkdir(parents=True, exist_ok=True)
    return [m for m in HF_MODELS if not (_DETECTORS / m).exists()]


def download_models(log: LogFn) -> None:
    """Download missing detector models from HuggingFace hub."""
    missing = missing_models()
    if not missing:
        log("[Setup] All models already present. Skipping download.\n")
        return

    # huggingface_hub is in the venv — use the venv Python to run a mini script
    for filename in missing:
        dest = _DETECTORS / filename
        log(f"[Setup] Downloading {filename} from HuggingFace ...\n")
        script = (
            "from huggingface_hub import hf_hub_download; "
            "import shutil; "
            f"path = hf_hub_download(repo_id='{HF_REPO_ID}', filename='{filename}'); "
            f"shutil.copy2(path, '{dest}')"
        )
        subprocess.run(
            [str(VENV_PYTHON), "-c", script],
            check=True,
        )
        log(f"[Setup] ✓ Downloaded: {filename}\n")


def run_full_setup(log: LogFn) -> None:
    """Run all setup steps in order."""
    create_venv(log)
    install_requirements(log)
    download_models(log)
    log("[Setup] ✅ Setup complete — ready to start the server.\n")
