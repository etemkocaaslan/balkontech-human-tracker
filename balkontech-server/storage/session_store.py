from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ultralytics import YOLO
from boxmot.trackers import ByteTrack

from schemas.sessions import SessionCreateRequest


@dataclass
class Session:
    session_id: str
    detector: YOLO
    tracker: ByteTrack
    config: SessionCreateRequest
    frame_idx: int = 0
    last_track_count: int = 0
    last_annotated_frame: Optional[bytes] = field(default=None, repr=False)
    # {zone_name: [track_id, ...]} — updated every frame
    zone_occupancy: Dict[str, List[int]] = field(default_factory=dict)


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
        session.frame_idx += 1
        return session.frame_idx

    def set_annotated_frame(self, session_id: str, jpeg_bytes: bytes) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.last_annotated_frame = jpeg_bytes

    def set_track_count(self, session_id: str, count: int) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.last_track_count = count

    def set_zone_occupancy(self, session_id: str, occupancy: Dict[str, List[int]]) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.zone_occupancy = occupancy

    def get_stats(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return {
            "session_id": session_id,
            "frame_index": session.frame_idx,
            "track_count": session.last_track_count,
            "zone_occupancy": session.zone_occupancy,
        }
