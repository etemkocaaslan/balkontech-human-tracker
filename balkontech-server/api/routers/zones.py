from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_zone_service, get_snapshot_service
from schemas.zones import (
    ZoneCreateRequest,
    ZoneInfo,
    ZoneUpdateRequest,
    SnapshotRequest,
    SnapshotResponse,
)
from services.zone_service import ZoneService
from services.snapshot_service import SnapshotService

router = APIRouter(prefix="/zones", tags=["Zones"])


# ── Snapshot ──────────────────────────────────────────────────────────────────

@router.post("/snapshot", response_model=SnapshotResponse)
def get_snapshot(
    req: SnapshotRequest,
    service: SnapshotService = Depends(get_snapshot_service),
):
    """Extract a reference frame from a video file for zone definition."""
    try:
        return service.extract(req.video_path, req.frame_index)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Zone CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[str], summary="List video IDs that have zones")
def list_video_ids(service: ZoneService = Depends(get_zone_service)):
    return service.list_video_ids()


@router.get("/{video_id}", response_model=List[ZoneInfo])
def list_zones(video_id: str, service: ZoneService = Depends(get_zone_service)):
    return service.list_zones(video_id)


@router.post("/{video_id}", response_model=ZoneInfo, status_code=201)
def create_zone(
    video_id: str,
    req: ZoneCreateRequest,
    service: ZoneService = Depends(get_zone_service),
):
    try:
        return service.create(video_id, req)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{video_id}/{zone_id}", response_model=ZoneInfo)
def get_zone(
    video_id: str,
    zone_id: str,
    service: ZoneService = Depends(get_zone_service),
):
    zone = service.get_zone(video_id, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found.")
    return zone


@router.put("/{video_id}/{zone_id}", response_model=ZoneInfo)
def update_zone(
    video_id: str,
    zone_id: str,
    req: ZoneUpdateRequest,
    service: ZoneService = Depends(get_zone_service),
):
    try:
        zone = service.update(video_id, zone_id, req)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found.")
    return zone


@router.delete("/{video_id}/{zone_id}", status_code=204)
def delete_zone(
    video_id: str,
    zone_id: str,
    service: ZoneService = Depends(get_zone_service),
):
    if not service.delete_zone(video_id, zone_id):
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found.")


@router.delete("/{video_id}", status_code=200)
def delete_all_zones(
    video_id: str,
    service: ZoneService = Depends(get_zone_service),
):
    count = service.delete_all(video_id)
    return {"deleted": count, "video_id": video_id}
