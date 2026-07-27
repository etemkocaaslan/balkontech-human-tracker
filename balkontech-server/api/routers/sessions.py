import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import (
    get_session_service,
    get_tracking_service,
    get_video_source_service,
    get_google_drive_service,
)
from schemas.sessions import SessionCreateRequest, SessionInfo, TrackRequest, TrackResponse
from schemas.video_source import VideoSourceRequest
from services.google_drive_service import GoogleDriveService
from services.session_service import SessionService
from services.tracking_service import TrackingService
from services.video_source_service import VideoSourceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _background_download_and_start(
    drive_file_id: str,
    session_id: str,
    video_source_svc: VideoSourceService,
    req: SessionCreateRequest,
    drive_svc: GoogleDriveService,
) -> None:
    """Download video from Drive then start VideoSourceService.

    Runs in a FastAPI BackgroundTask so the POST /sessions handler
    returns immediately and the download does not block the event loop.
    """
    try:
        video_source_svc._store.set_video_pipeline_status(session_id, "downloading")
        logger.info("Background download started for session %s (file_id=%s)", session_id[:8], drive_file_id)

        file_name = f"{session_id}.mp4"
        local_path = drive_svc.download_file(
            file_id=drive_file_id,
            file_name=file_name,
        )

        if local_path is None:
            video_source_svc._store.set_video_pipeline_status(session_id, "error")
            logger.warning("Drive download failed for session %s", session_id[:8])
            return

        video_source_svc._store.set_video_pipeline_status(session_id, "running")
        logger.info(
            "Drive download complete for session %s → %s",
            session_id[:8], local_path,
        )

        video_source_svc.start(
            session_id,
            VideoSourceRequest(
                video_path=str(local_path),
                video_id=req.video_id or Path(file_name).stem,
                det_skip=req.det_skip,
                fps_target=req.fps_target,
                loop=req.loop,
            ),
        )
        logger.info("VideoSourceService started for session %s", session_id[:8])

    except Exception as exc:
        logger.exception("Background download error for session %s", session_id[:8])
        video_source_svc._store.set_video_pipeline_status(session_id, "error")


@router.post("", response_model=SessionInfo, status_code=201)
def create_session(
    req: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
    video_source_svc: VideoSourceService = Depends(get_video_source_service),
    drive_svc: GoogleDriveService = Depends(get_google_drive_service),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    try:
        info = service.create(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if req.drive_file_id:
        video_source_svc._store.set_video_pipeline_status(info.session_id, "preparing")
        background_tasks.add_task(
            _background_download_and_start,
            req.drive_file_id,
            info.session_id,
            video_source_svc,
            req,
            drive_svc,
        )
        logger.info(
            "Session %s created (drive_file_id=%s) — background download queued",
            info.session_id[:8], req.drive_file_id[:16],
        )
        return info

    if req.video_path:
        try:
            video_source_svc.start(
                info.session_id,
                VideoSourceRequest(
                    video_path=req.video_path,
                    video_id=req.video_id,
                    det_skip=req.det_skip,
                    fps_target=req.fps_target,
                    loop=req.loop,
                ),
            )
            logger.info("Video source started for session %s → %s", info.session_id[:8], req.video_path)
        except Exception as exc:
            logger.warning("Could not start video source for session %s: %s", info.session_id[:8], exc)

    return info


@router.post("/{session_id}/track", response_model=TrackResponse)
def track_frame(
    session_id: str,
    body: TrackRequest,
    tracking_svc: TrackingService = Depends(get_tracking_service),
):
    """Process a single base64-encoded frame and return track results."""
    try:
        return tracking_svc.process_frame(session_id, body.frame_b64, video_id=body.video_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{session_id}/stats")
def get_stats(
    session_id: str,
    service: TrackingService = Depends(get_tracking_service),
):
    stats = service.get_stats(session_id)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return stats


@router.get("", response_model=List[SessionInfo])
def list_sessions(service: SessionService = Depends(get_session_service)):
    return service.list_sessions()


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    if not service.delete(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")


class DisplayOptions(BaseModel):
    show_id: bool


@router.patch("/{session_id}/display", status_code=200)
def update_display(
    session_id: str,
    opts: DisplayOptions,
    service: SessionService = Depends(get_session_service),
):
    """Toggle display options (e.g. show/hide track ID) on a live session."""
    ok = service.set_display_options(session_id, show_id=opts.show_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"session_id": session_id, "show_id": opts.show_id}
