import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import get_session_service, get_tracking_service
from services.session_service import SessionService
from services.tracking_service import TrackingService

router = APIRouter(prefix="/sessions", tags=["Stream"])


def _placeholder_jpeg() -> bytes:
    import cv2
    import numpy as np
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.putText(img, "Waiting for frames...", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


@router.get("/{session_id}/stream", summary="MJPEG live stream of tracked frames")
async def mjpeg_stream(
    session_id: str,
    session_svc: SessionService = Depends(get_session_service),
    tracking_svc: TrackingService = Depends(get_tracking_service),
):
    if not session_svc.exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    placeholder = _placeholder_jpeg()

    async def generate():
        last_frame = placeholder
        while True:
            if not session_svc.exists(session_id):
                break
            frame = tracking_svc.get_latest_frame(session_id)
            if frame is not None:
                last_frame = frame
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + last_frame + b"\r\n"
            await asyncio.sleep(0.033)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
