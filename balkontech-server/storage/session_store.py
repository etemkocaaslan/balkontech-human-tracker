from dataclasses import dataclass, field
from typing import Dict, List, Optional

from typing import Any
from ultralytics import YOLO

from schemas.sessions import SessionCreateRequest


@dataclass
class Session:
    session_id: str
    detector: YOLO
    tracker: Any  # any BoxMOT tracker (ByteTrack, BotSort, StrongSort, …)
    config: SessionCreateRequest
    frame_index: int = 0
    last_track_count: int = 0
    last_annotated_frame: Optional[bytes] = field(default=None, repr=False)
    # {zone_name: [track_id, ...]} — updated every frame
    zone_occupancy: Dict[str, List[int]] = field(default_factory=dict)
    # Display options — can be toggled at runtime via PATCH /sessions/{id}/display
    show_id: bool = True
    # Pipeline status — set by the background download/preparation flow.
    # Values: None (legacy/direct video_path), "preparing", "downloading", "running", "error"
    video_pipeline_status: Optional[str] = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def create(self, session_id: str, detector, tracker, config) -> Session:
        session = Session(session_id=session_id, detector=detector, tracker=tracker, config=config)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_ids(self) -> List[str]:
        return list(self._sessions.keys())

    def increment_frame(self, session_id: str) -> int:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session '{session_id}' not found.")
        session.frame_index += 1
        return session.frame_index

    def set_annotated_frame(self, session_id: str, jpeg_bytes: bytes) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.last_annotated_frame = jpeg_bytes

    def set_track_count(self, session_id: str, count: int) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.last_track_count = count

    def set_display_options(self, session_id: str, *, show_id: bool) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.show_id = show_id

    def set_zone_occupancy(self, session_id: str, occupancy: Dict[str, List[int]]) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.zone_occupancy = occupancy

    def set_video_pipeline_status(self, session_id: str, status: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.video_pipeline_status = status

    def get_stats(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return {
            "session_id": session_id,
            "frame_index": session.frame_index,
            "track_count": session.last_track_count,
            "zone_occupancy": session.zone_occupancy,
            "pipeline_status": session.video_pipeline_status,
        }
