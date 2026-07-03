# balkontech-client

PyQt6 desktop application for Balkontech Human Tracker. Connects to a running `balkontech-server`, displays the live MJPEG stream, and shows real-time zone occupancy.

## Prerequisites

- Python 3.10 – 3.12
- A running `balkontech-server` (see [`../balkontech-server/README.md`](../balkontech-server/README.md))
- An API key created in the server's admin panel

## Installation

```bash
cd balkontech-client
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

> **Windows note:** The pinned versions in `requirements.txt` are required to avoid a PyQt6 DLL load error on Windows. Do not upgrade PyQt6 without testing first.

## Running

```bash
python main.py
```

## First-time setup

1. Start the server and open `http://127.0.0.1:8000` in a browser
2. Go to **🔑 API Keys** and create a key — copy the raw key shown once
3. In the client, click **⚙ Settings** and paste the server URL + API key
4. Click **+ New Session**, select a model and video file, then **Create**
5. Select the session from the list and click **▶ Connect**

## Zone editor

Zones are defined in the browser at `http://127.0.0.1:8000` → **⬡ Zone Editor** tab (or directly at `/zone-editor`). Zones are stored server-side and applied automatically to any session using the matching video ID.

## Configuration

Settings (server URL and API key) are persisted in the OS registry (Windows) or `~/.config` (Linux/macOS) under `Balkontech / HumanTracker`. Change them anytime via **⚙ Settings**.
