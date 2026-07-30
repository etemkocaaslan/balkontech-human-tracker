"""
Upload router — accepts video files from remote clients.

POST /upload  →  saves to videos/ directory, returns metadata the
                  client uses to create a session via video_path.
"""

import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

logger = logging.getLogger(__name__)

_VIDEOS_DIR = Path(os.getenv("VIDEOS_DIR", Path(__file__).resolve().parents[2] / "videos"))

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv"}

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("", status_code=201)
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file to the server.

    Returns the server-side path and a video_id derived from the filename stem,
    which can be passed directly to POST /sessions as video_path and video_id.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Unique filename to avoid collisions across concurrent uploads
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    _VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _VIDEOS_DIR / unique_name

    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    except Exception as exc:
        logger.exception("Failed to save uploaded file: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save file on server.")
    finally:
        await file.close()

    size_bytes = dest.stat().st_size
    video_id = Path(file.filename or unique_name).stem

    logger.info(
        "Video uploaded: %s → %s (%.1f MB)",
        file.filename, dest.name, size_bytes / 1_048_576,
    )

    return {
        "filename": file.filename,
        "stored_name": unique_name,
        "video_path": str(dest),
        "video_id": video_id,
        "size_bytes": size_bytes,
    }
