"""
Zone Service — API Test Script

Kullanim:
    python test_zones.py
    python test_zones.py --video "out_1917_1080.mp4"
    python test_zones.py --video "out_1917_1080.mp4" --frame 150
"""

import argparse
import base64
import json
import sys
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"
VIDEO_ID = "test_video"


def ok(label, resp):
    status = "✓" if resp.ok else "✗"
    print(f"\n{status} {label} [{resp.status_code}]")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text[:300])
    return resp.ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default="out_1917_1080.mp4")
    parser.add_argument("--frame", type=int, default=0)
    args = parser.parse_args()

    print("=" * 60)
    print("  BoxMOT Zone Service Test")
    print("=" * 60)

    # ── 1. Health ─────────────────────────────────────────────────
    r = requests.get(f"{BASE_URL}/health")
    if not ok("GET /health", r):
        print("\nServis çalışmıyor. Önce uvicorn'u başlat.")
        sys.exit(1)

    # ── 2. Snapshot ───────────────────────────────────────────────
    print("\n── Snapshot ──────────────────────────────────────────────")
    r = requests.post(f"{BASE_URL}/zones/snapshot", json={
        "video_path": args.video,
        "frame_index": args.frame,
    })
    snapshot_ok = ok("POST /zones/snapshot", r)
    width, height = 1920, 1080   # fallback defaults

    if snapshot_ok:
        data = r.json()
        width  = data["width"]
        height = data["height"]
        print(f"\n  → Frame boyutu: {width}×{height}")

        # Save snapshot to disk for visual inspection
        img_path = Path("snapshot_reference.jpg")
        img_path.write_bytes(base64.b64decode(data["frame_b64"]))
        print(f"  → Referans frame kaydedildi: {img_path.resolve()}")
        print("    Bu görüntü üzerinde zone noktalarını belirleyebilirsin.")

    # ── 3. Zone oluştur ───────────────────────────────────────────
    print("\n── Zone Oluşturma ────────────────────────────────────────")

    # İlk zone — sol üst bölge
    r = requests.post(f"{BASE_URL}/zones/{VIDEO_ID}", json={
        "name": "Assembly Station A",
        "description": "Sol üst köşe",
        "pixel_points": [
            {"x": width * 0.10, "y": height * 0.10},
            {"x": width * 0.40, "y": height * 0.10},
            {"x": width * 0.40, "y": height * 0.50},
            {"x": width * 0.10, "y": height * 0.50},
        ],
        "reference_width": width,
        "reference_height": height,
    })
    ok("POST /zones/test_video (Station A)", r)
    zone_a_id = r.json().get("id") if r.ok else None

    # İkinci zone — sağ alt bölge
    r = requests.post(f"{BASE_URL}/zones/{VIDEO_ID}", json={
        "name": "Assembly Station B",
        "description": "Sağ alt köşe",
        "pixel_points": [
            {"x": width * 0.60, "y": height * 0.50},
            {"x": width * 0.90, "y": height * 0.50},
            {"x": width * 0.90, "y": height * 0.90},
            {"x": width * 0.60, "y": height * 0.90},
        ],
        "reference_width": width,
        "reference_height": height,
    })
    ok("POST /zones/test_video (Station B)", r)

    # ── 4. Listele ────────────────────────────────────────────────
    print("\n── Zone Listeleme ────────────────────────────────────────")
    r = requests.get(f"{BASE_URL}/zones/{VIDEO_ID}")
    ok("GET /zones/test_video", r)

    if r.ok:
        zones = r.json()
        print(f"\n  → {len(zones)} zone kayıtlı:")
        for z in zones:
            pts = z["points"]
            print(f"    [{z['name']}] id={z['id'][:8]}... | {len(pts)} nokta | "
                  f"ref={z['reference_resolution']['width']}×{z['reference_resolution']['height']}")

    # ── 5. Tek zone getir ─────────────────────────────────────────
    if zone_a_id:
        print("\n── Tek Zone ─────────────────────────────────────────────")
        r = requests.get(f"{BASE_URL}/zones/{VIDEO_ID}/{zone_a_id}")
        ok(f"GET /zones/test_video/{zone_a_id[:8]}...", r)

    # ── 6. Zone güncelle ──────────────────────────────────────────
    if zone_a_id:
        print("\n── Zone Güncelleme ───────────────────────────────────────")
        r = requests.put(f"{BASE_URL}/zones/{VIDEO_ID}/{zone_a_id}", json={
            "name": "Assembly Station A — Updated",
            "description": "Yeni açıklama",
        })
        ok(f"PUT /zones/test_video/{zone_a_id[:8]}...", r)

    # ── 7. Duplicate isim testi ───────────────────────────────────
    print("\n── Duplicate İsim Testi (409 bekleniyor) ─────────────────")
    r = requests.post(f"{BASE_URL}/zones/{VIDEO_ID}", json={
        "name": "Assembly Station B",
        "pixel_points": [
            {"x": 10, "y": 10}, {"x": 100, "y": 10}, {"x": 100, "y": 100}
        ],
        "reference_width": width,
        "reference_height": height,
    })
    ok("POST /zones/test_video (duplicate name)", r)

    # ── 8. Video ID listesi ───────────────────────────────────────
    print("\n── Video ID Listesi ──────────────────────────────────────")
    r = requests.get(f"{BASE_URL}/zones")
    ok("GET /zones", r)

    # ── 9. Zone sil ───────────────────────────────────────────────
    if zone_a_id:
        print("\n── Zone Silme ────────────────────────────────────────────")
        r = requests.delete(f"{BASE_URL}/zones/{VIDEO_ID}/{zone_a_id}")
        ok(f"DELETE /zones/test_video/{zone_a_id[:8]}...", r)

        # Silindiğini doğrula
        r = requests.get(f"{BASE_URL}/zones/{VIDEO_ID}/{zone_a_id}")
        ok(f"GET (silinmiş zone — 404 bekleniyor)", r)

    # ── 10. Tümünü sil ────────────────────────────────────────────
    print("\n── Tümünü Silme ──────────────────────────────────────────")
    r = requests.delete(f"{BASE_URL}/zones/{VIDEO_ID}")
    ok(f"DELETE /zones/test_video (tümü)", r)

    r = requests.get(f"{BASE_URL}/zones/{VIDEO_ID}")
    zones_after = r.json() if r.ok else []
    print(f"\n  → Kalan zone sayısı: {len(zones_after)} (0 bekleniyor)")

    print("\n" + "=" * 60)
    print("  Test tamamlandı.")
    print("=" * 60)


if __name__ == "__main__":
    main()
