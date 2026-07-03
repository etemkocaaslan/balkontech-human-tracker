# balkontech-client

PyQt6 desktop application for Balkontech Human Tracker. Connects to a running `balkontech-server`, displays the live MJPEG stream, and shows real-time zone occupancy statistics.

## Prerequisites

- Python 3.10 – 3.12
- A running `balkontech-server` — see [`../balkontech-server/README.md`](../balkontech-server/README.md)
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

> **Windows note:** The pinned PyQt6 versions in `requirements.txt` are required to avoid a DLL load error on Windows. Do not upgrade PyQt6 without testing first.

## Running

```bash
python main.py
```

## First-time setup

1. Start the server and open `http://127.0.0.1:8000` in a browser
2. Go to **🔑 API Keys** → create a key and copy the raw value shown once
3. In the client, click **⚙ Settings** and enter the server URL and API key
4. Click **+ New Session**, select a model and a video file, then click **Create**
5. Select the session from the list and click **▶ Connect**

## Zone editor

Zones are defined in the browser at `http://127.0.0.1:8000` → **⬡ Zone Editor** tab (or directly at `http://127.0.0.1:8000/zone-editor`).

Zones are stored server-side and automatically applied to any session that uses the matching video file.

## Settings persistence

The server URL and API key are saved in the OS registry (Windows) or `~/.config` (Linux/macOS) under `Balkontech/HumanTracker`. They can be updated anytime via **⚙ Settings**.
