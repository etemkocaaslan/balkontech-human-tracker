from pydantic import BaseModel, computed_field


class ModelInfo(BaseModel):
    name: str        # filename, e.g. "yolov8n.pt"
    type: str        # "detector" or "reid"
    size_mb: float
    path: str        # absolute path inside container

    @computed_field
    @property
    def has_detector(self) -> bool:
        return self.type == "detector"

    @computed_field
    @property
    def has_reid(self) -> bool:
        return self.type == "reid"
