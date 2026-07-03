# balkontech-server

FastAPI service that runs YOLO detection + ByteTrack multi-object tracking and streams annotated frames over MJPEG.

## Prerequisites

- Python 3.10 – 3.12
- A YOLO detector model (`.pt` file) — downloaded automatically on first boot, or place manually

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

Models are downloaded automatically on first boot if the directories are empty.

To use custom models, place `.pt` files under:

```
balkontech-server/
└── models/
    ├── detectors/
    │   └── yolov8n.pt
    └── reid/
        └── osnet_x0_25_msmt17.pt   (optional)
```

## API keys

The server ships with no keys by default. Copy the example file before first run:

```bash
cp api_keys.json.example api_keys.json
```

Then create real keys through the admin panel (the example file is a format reference only).

## Running

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000` | Admin panel (Stream · Zone Editor · Models · API Keys) |
| `http://127.0.0.1:8000/zone-editor` | Standalone zone editor |
| `http://127.0.0.1:8000/docs` | Interactive API docs |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODELS_DIR` | `./models` | Directory scanned for `.pt` model files |
| `ZONES_DIR` | `./zones` | Directory where zone JSON files are stored |
| `API_KEYS_FILE` | `./api_keys.json` | Path to the API keys store |

## Key API endpoints

All endpoints under `/api/v1/` require the `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/sessions` | List active sessions |
| POST | `/api/v1/sessions` | Create session (auto-starts video source if `video_path` given) |
| DELETE | `/api/v1/sessions/{id}` | Stop and delete session |
| GET | `/api/v1/sessions/{id}/stream` | MJPEG stream |
| GET | `/api/v1/sessions/{id}/stats` | Zone occupancy stats |
| GET | `/api/v1/models` | List available models |
| GET/POST | `/zones/{video_id}` | List / create zones (admin, no auth) |

## Docker (optional)

```bash
docker compose up --build
```

> Requires Docker Desktop. `api_keys.json` and `models/` must exist before starting.
