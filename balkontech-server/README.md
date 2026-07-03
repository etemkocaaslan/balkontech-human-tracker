# balkontech-server

FastAPI service that runs YOLO detection + ByteTrack multi-object tracking and streams annotated frames over MJPEG.

## Prerequisites

- Python 3.10 – 3.12
- (Optional) CUDA 11.8+ for GPU inference

## Installation

```bash
cd balkontech-server
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Model setup

**Standard models** (`yolov8n.pt`, `osnet_x0_25_msmt17.pt`) are downloaded automatically on first boot — no action required.

**Custom / fine-tuned models** are hosted on [Hugging Face](https://huggingface.co/etemkocaaslan/balkontech-models). Set the following environment variables before starting the server and they will be downloaded automatically:

```bash
# Windows
set HF_MODEL_REPO=etemkocaaslan/balkontech-models
set HF_MODELS=yolo11x_best.pt,yolo26x_best.pt

# Linux / macOS
export HF_MODEL_REPO=etemkocaaslan/balkontech-models
export HF_MODELS=yolo11x_best.pt,yolo26x_best.pt
```

After download, models appear in `models/detectors/` and can be selected from the admin panel.

### Adding new models to Hugging Face (maintainers only)

```bash
pip install huggingface_hub
huggingface-cli login
huggingface-cli upload etemkocaaslan/balkontech-models <local_path/model.pt> <model.pt>
```

## API keys

The server ships with no keys. Copy the example file before first run:

```bash
# Windows
copy api_keys.json.example api_keys.json
# Linux / macOS
cp api_keys.json.example api_keys.json
```

Then open the admin panel at `http://127.0.0.1:8000` → **🔑 API Keys** to create real keys. The example file is a format reference only.

## Running

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000` | Admin panel (Stream · Zone Editor · Models · API Keys) |
| `http://127.0.0.1:8000/zone-editor` | Standalone zone editor |
| `http://127.0.0.1:8000/docs` | Interactive API docs (Swagger) |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODELS_DIR` | `./models` | Directory scanned for `.pt` model files |
| `ZONES_DIR` | `./zones` | Directory where zone JSON files are stored |
| `API_KEYS_FILE` | `./api_keys.json` | Path to the API keys store |
| `HF_MODEL_REPO` | *(unset)* | Hugging Face repo ID for custom models |
| `HF_MODELS` | *(unset)* | Comma-separated `.pt` filenames to download from `HF_MODEL_REPO` |

## Key API endpoints

All endpoints under `/api/v1/` require an `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/sessions` | List active sessions |
| POST | `/api/v1/sessions` | Create a session |
| DELETE | `/api/v1/sessions/{id}` | Stop and remove a session |
| GET | `/api/v1/sessions/{id}/stream` | MJPEG video stream |
| GET | `/api/v1/sessions/{id}/stats` | Zone occupancy statistics |
| GET | `/api/v1/models` | List available models |
| GET/POST | `/zones/{video_id}` | List / create zones (admin, no auth required) |

## Docker (optional)

```bash
docker compose up --build
```

> Requires Docker Desktop. `api_keys.json` must exist before starting. Set `HF_MODEL_REPO` and `HF_MODELS` in `docker-compose.yml` if custom models are needed.
