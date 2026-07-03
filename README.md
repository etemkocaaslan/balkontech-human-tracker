# Balkontech Human Tracker

Real-time human detection and zone-based tracking system built with [BoxMOT](https://github.com/mikel-brostrom/boxmot) (ByteTrack) and Ultralytics YOLO.

```
┌─────────────────────────┐        HTTP / MJPEG         ┌──────────────────────┐
│        Client           │ ◄─────────────────────────► │       Server         │
│   PyQt6 desktop app     │                             │ FastAPI + ByteTrack  │
└─────────────────────────┘                             └──────────────────────┘
```

## Repository layout

```
balkontech-human-tracker/
├── balkontech-server/   # FastAPI tracking service
└── balkontech-client/   # PyQt6 desktop client
```

## Quick start

1. **Start the server** — see [`balkontech-server/README.md`](balkontech-server/README.md)
2. **Launch the client** — see [`balkontech-client/README.md`](balkontech-client/README.md)
3. Open the admin panel at `http://127.0.0.1:8000`, create an API key under **🔑 API Keys**
4. Enter the key in the client via **⚙ Settings**

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.10 – 3.12 |
| CUDA (optional) | 11.8 + |

## License

Proprietary — Balkontech. All rights reserved.
