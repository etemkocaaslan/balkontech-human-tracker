from typing import List, Optional
from pydantic import BaseModel, Field


class TrackerParams(BaseModel):
    track_buffer: int = 90
    frame_rate: int = 30
    max_age: int = 90
    track_thresh: float = 0.35
    min_conf: float = 0.1
    match_thresh: float = 0.85
    min_hits: int = 1
    iou_threshold: float = 0.3
    per_class: bool = False


class SessionCreateRequest(BaseModel):
    detector_model: str = Field(..., json_schema_extra={"example": "yolov8n.pt"})
    tracker_type: str = "bytetrack"
    tracker_params: TrackerParams = Field(default_factory=TrackerParams)
    conf_threshold: float = 0.25
    nms_iou_threshold: float = 0.45
    target_classes: Optional[List[int]] = Field(default_factory=lambda: [0])
    imgsz: int = 640
    device: str = "cpu"
    # ReID model — required for appearance-based trackers (boosttrack, botsort, strongsort, …)
    reid_model: Optional[str] = Field(
        None,
        description="ReID model filename in models/reid/ (e.g. 'osnet_x0_25_msmt17.pt'). "
                    "Required for appearance-based trackers; ignored for bytetrack / ocsort.",
    )
    # Optional video source — when provided, the backend reads the video directly
    video_path: Optional[str] = Field(None, description="Path to a video file on the server machine.")
    video_id: Optional[str] = Field(None, description="Zone lookup key; defaults to the filename stem.")
    # Google Drive file reference — when set, the server downloads the video from Drive
    # instead of reading video_path directly. This is the primary transfer mechanism
    # for the upload→create_session pipeline (video_path is ignored when drive_file_id is present).
    drive_file_id: Optional[str] = Field(
        None,
        description="Google Drive file ID of the uploaded video. When provided, the server "
                    "downloads the video from Drive before starting tracking. "
                    "Takes precedence over video_path.",
    )
    det_skip: int = Field(2, ge=1, le=10, description="Run YOLO every N frames; tracker predicts in between.")
    fps_target: float = Field(25.0, gt=0, le=120)
    loop: bool = Field(False, description="Loop the video when it ends.")


class SessionInfo(BaseModel):
    session_id: str
    detector_model: str
    tracker_type: str
    device: str
    target_classes: Optional[List[int]]
    # Current pipeline status — None means the session's video source
    # is already running (legacy) or status is not tracked.
    status: Optional[str] = Field(
        None,
        description="Session pipeline status: 'preparing', 'downloading', "
                    "'running', 'error'. None for sessions created "
                    "with video_path directly (legacy path).",
    )


class TrackRequest(BaseModel):
    frame_b64: str
    video_id: Optional[str] = Field(
        None,
        description="When provided, zones defined for this video will be overlaid on the stream.",
    )


class TrackedObject(BaseModel):
    track_id: int
    bbox: List[float]
    confidence: float
    class_id: int


class TrackResponse(BaseModel):
    session_id: str
    frame_index: int
    tracks: List[TrackedObject]
