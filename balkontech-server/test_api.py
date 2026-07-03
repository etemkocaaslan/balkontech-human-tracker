"""
BoxMOT Service — API Test Script

Kullanım:
    python test_api.py --video out_1917_1080.mp4
    python test_api.py --video out_1917_1080.mp4 --frames 20 --model yolov8n.pt
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import cv2
import requests

BASE_URL = "http://127.0.0.1:8000"


def encode_frame(frame) -> str:
    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf).decode("utf-8")


def print_result(label: str, resp: requests.Response):
    status = "✓" if resp.ok else "✗"
    print(f"\n{status} {label} [{resp.status_code}]")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default="0",
                        help="Video source (0=webcam or file path)")
    parser.add_argument("--frames", type=int, default=5,
                        help="Number of frames to test")
    parser.add_argument("--model", default="yolov8n.pt",
                        help="Detector model name")
    args = parser.parse_args()

    # ── 1. Health check ───────────────────────────────────────────────────────
    r = requests.get(f"{BASE_URL}/health")
    print_result("GET /health", r)
    if not r.ok:
        print("Service is not reachable. Is it running?")
        sys.exit(1)

    # ── 2. List models ────────────────────────────────────────────────────────
    r = requests.get(f"{BASE_URL}/models")
    print_result("GET /models", r)

    # ── 3. Create session ─────────────────────────────────────────────────────
    create_payload = {
        "detector_model": args.model,
        "tracker_type": "bytetrack",
        "tracker_params": {
            "track_buffer": 90,
            "max_age": 90,
            "track_thresh": 0.35,
            "match_thresh": 0.85,
            "min_hits": 1,
        },
        "conf_threshold": 0.25,
        "nms_iou_threshold": 0.45,
        "target_classes": [0],
        "imgsz": 640,
        "device": "cpu",
    }
    r = requests.post(f"{BASE_URL}/sessions", json=create_payload)
    print_result("POST /sessions", r)
    if not r.ok:
        sys.exit(1)

    session_id = r.json()["session_id"]

    # ── 4. Open video source ──────────────────────────────────────────────────
    source = int(args.video) if args.video == "0" else args.video
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"\n✗ Could not open source: {args.video}")
        sys.exit(1)

    # Derive video_id from filename stem for zone overlay (skipped for webcam)
    video_id = Path(args.video).stem if args.video != "0" else None

    print(f"\n── Sending {args.frames} frame(s) ── session={session_id} video_id={video_id} ──")

    for i in range(args.frames):
        ret, frame = cap.read()
        if not ret:
            print("  Video ended early.")
            break

        track_payload: dict = {"frame_b64": encode_frame(frame)}
        if video_id:
            track_payload["video_id"] = video_id

        start = time.perf_counter()
        r = requests.post(
            f"{BASE_URL}/sessions/{session_id}/track",
            json=track_payload,
        )
        elapsed = (time.perf_counter() - start) * 1000

        if r.ok:
            data = r.json()
            tracks = data["tracks"]
            print(
                f"  Frame {i+1:02d} | {elapsed:.0f}ms | {len(tracks)} track(s): "
                + ", ".join(
                    f"ID={t['track_id']} cls={t['class_id']} conf={t['confidence']:.2f}"
                    for t in tracks
                )
            )
        else:
            print(f"  Frame {i+1:02d} | ERROR {r.status_code}: {r.text}")

    cap.release()

    # ── 5. Stats ──────────────────────────────────────────────────────────────
    r = requests.get(f"{BASE_URL}/sessions/{session_id}/stats")
    print_result(f"GET /sessions/{session_id}/stats", r)

    # ── 6. Delete session ─────────────────────────────────────────────────────
    r = requests.delete(f"{BASE_URL}/sessions/{session_id}")
    status = "✓" if r.status_code == 204 else "✗"
    print(f"\n{status} DELETE /sessions/{session_id} [{r.status_code}]")

    print("\n── Test complete ──")


if __name__ == "__main__":
    main()
