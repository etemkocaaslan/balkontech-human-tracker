from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class ZonePoint(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized x coordinate [0.0 - 1.0]")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized y coordinate [0.0 - 1.0]")


class PixelPoint(BaseModel):
    x: float = Field(..., ge=0, description="Pixel x coordinate")
    y: float = Field(..., ge=0, description="Pixel y coordinate")


class Resolution(BaseModel):
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class ZoneCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    pixel_points: List[PixelPoint] = Field(..., min_length=3, description="Minimum 3 points for a polygon")
    reference_width: int = Field(..., gt=0, description="Frame width used when defining points")
    reference_height: int = Field(..., gt=0, description="Frame height used when defining points")

    @model_validator(mode="after")
    def check_min_points(self) -> ZoneCreateRequest:
        if len(self.pixel_points) < 3:
            raise ValueError("A zone requires at least 3 points.")
        return self


class ZoneUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    description: Optional[str] = None
    pixel_points: Optional[List[PixelPoint]] = Field(None, min_length=3)
    reference_width: Optional[int] = Field(None, gt=0)
    reference_height: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def check_points_with_resolution(self) -> ZoneUpdateRequest:
        has_points = self.pixel_points is not None
        has_res = self.reference_width is not None and self.reference_height is not None
        if has_points and not has_res:
            raise ValueError("reference_width and reference_height are required when updating points.")
        return self


class ZoneInfo(BaseModel):
    id: str
    name: str
    description: Optional[str]
    points: List[ZonePoint]                  # normalized [0.0 - 1.0]
    reference_resolution: Resolution
    created_at: datetime
    active: bool


class SnapshotRequest(BaseModel):
    video_path: str = Field(..., description="Path to the video file")
    frame_index: int = Field(0, ge=0, description="Which frame to extract (0 = first frame)")


class SnapshotResponse(BaseModel):
    video_path: str
    frame_index: int
    width: int
    height: int
    frame_b64: str                           # JPEG base64 — use as canvas for zone definition
