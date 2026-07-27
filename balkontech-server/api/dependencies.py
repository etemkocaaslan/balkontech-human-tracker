from functools import lru_cache

from storage.model_store import ModelStore
from storage.session_store import SessionStore
from storage.zone_store import ZoneStore
from storage.api_key_store import ApiKeyStore
from storage.model_bootstrapper import ModelBootstrapper
from services.google_drive_service import GoogleDriveService
from services.model_service import ModelService
from services.session_service import SessionService
from services.tracking_service import TrackingService
from services.video_source_service import VideoSourceService
from services.zone_service import ZoneService
from services.snapshot_service import SnapshotService


@lru_cache(maxsize=1)
def get_model_store() -> ModelStore:
    return ModelStore()

@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    return SessionStore()

@lru_cache(maxsize=1)
def get_zone_store() -> ZoneStore:
    return ZoneStore()

@lru_cache(maxsize=1)
def get_api_key_store() -> ApiKeyStore:
    return ApiKeyStore()

@lru_cache(maxsize=1)
def get_model_service() -> ModelService:
    return ModelService(registry=get_model_store(), bootstrapper=ModelBootstrapper())

def get_session_service() -> SessionService:
    return SessionService(session_store=get_session_store(), model_registry=get_model_store())

def get_zone_service() -> ZoneService:
    return ZoneService(store=get_zone_store())

@lru_cache(maxsize=1)
def get_tracking_service() -> TrackingService:
    return TrackingService(
        session_store=get_session_store(),
        zone_service=get_zone_service(),
    )

@lru_cache(maxsize=1)
def get_snapshot_service() -> SnapshotService:
    return SnapshotService()

@lru_cache(maxsize=1)
def get_google_drive_service() -> GoogleDriveService:
    return GoogleDriveService()

@lru_cache(maxsize=1)
def get_video_source_service() -> VideoSourceService:
    return VideoSourceService(
        session_store=get_session_store(),
        zone_service=get_zone_service(),
    )
