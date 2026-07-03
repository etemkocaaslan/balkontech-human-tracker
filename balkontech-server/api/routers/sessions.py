import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_session_service, get_tracking_service, get_video_source_service
from schemas.sessions import SessionCreateRequest, SessionInfo, TrackRequest, TrackResponse
from schemas.video_source import VideoSourceRequest
from services.session_service import SessionService
from services.tracking_service import TrackingService
from services.video_source_service import VideoSourceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionInfo, status_code=201)
def create_session(
    req: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
    video_source_svc: VideoSourceService = Depends(get_video_source_service),
):
    try:
        info = service.create(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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


@router.get("", response_model=List[str])
def list_sessions(service: SessionService = Depends(get_session_service)):
    return service.get_session_ids()


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    if not service.delete(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
