from typing import Literal, Optional
from pydantic import BaseModel, Field


class VideoSourceRequest(BaseModel):
    video_path: str = Field(
        ...,
        description="Path to the video file. Resolved relative to the service root or as absolute.",
        json_schema_extra={"example": "out_1917_1080.mp4"},
    )
    video_id: Optional[str] = Field(
        None,
        description="Video ID used to look up zones. Defaults to the filename stem.",
    )
    det_skip: int = Field(
        2,
        ge=1,
        le=10,
        description="Run YOLO every N frames; ByteTrack predicts in-between frames.",
    )
    fps_target: float = Field(
        25.0,
        gt=0,
        le=120,
        description="Target processing FPS. Service sleeps between frames to match this rate.",
    )
    loop: bool = Field(
        False,
        description="Loop the video when it ends.",
    )


class VideoSourceStatus(BaseModel):
    session_id: str
    status: Literal["running", "stopped", "error", "finished"]
    video_path: str
    frame_index: int
    fps_actual: float
    det_skip: int
    loop: bool
    error: Optional[str] = None
