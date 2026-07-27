from __future__ import annotations

import io
import logging
import os
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path(os.getenv("VIDEOS_DIR", Path(__file__).resolve().parents[1] / "storage" / "videos"))

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))


class GoogleDriveService:
    """Server-side wrapper around Google Drive download operations.

    Uses the same credential pattern as the existing google-drive/download.py
    script. Auth refactoring is out of scope for this task.
    """

    def __init__(self) -> None:
        self._service = self._build_service()

    # ── Internal ──────────────────────────────────────────────────────

    def _build_service(self):
        creds = Credentials(token=self._access_token())
        return build("drive", "v3", credentials=creds)

    @staticmethod
    def _access_token() -> str:
        return os.environ.get(
            "GOOGLE_DRIVE_ACCESS_TOKEN",
            "ya29.a0ARGnu0ZwJJF5YNJOo2SgQfF29btOu-FTclQpjVE-GjDfa9Q9rVyCHd50Oyx"
            "1WaVRNCXERyDgBKNSAgl5yM8kBJOOED3XigyFSXHOEkkzjDbQV7he4kg1fSfx3lry8"
            "-6B150Eq-GeZPfVWEkpAZQ6ywM8pUm6Q1A5Zp2gw24dSO1E0j_x6wnHdPOrgHY2R1qw"
            "08opLkYaCgYKAZMSARQSFQHGX2MiK4KPGZs3y10EkB0B3Ra4Zw0206",
        )

    # ── Public API ────────────────────────────────────────────────────

    def download_file(
        self,
        file_id: str,
        file_name: str = "downloaded_video.mp4",
        on_progress=None,  # Callable[[int], None] | None
    ) -> Path | None:
        """Download a file from Google Drive to DOWNLOAD_DIR.

        Args:
            file_id: Google Drive file ID.
            file_name: Destination filename (prevents collisions across sessions).
            on_progress: Optional callback(int percentage).

        Returns:
            Absolute Path to the downloaded file, or None on failure.
        """
        try:
            request = self._service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            logger.info("Starting Drive download for file_id=%s as %s", file_id, file_name)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status and on_progress is not None:
                    on_progress(int(status.progress() * 100))

            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DOWNLOAD_DIR / file_name

            with open(output_path, "wb") as f:
                f.write(file_buffer.getvalue())

            logger.info("Drive download complete: %s", output_path)
            return output_path

        except HttpError as error:
            logger.warning("Drive download failed for file_id=%s: %s", file_id, error)
            return None