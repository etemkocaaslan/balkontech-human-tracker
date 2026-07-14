"""
ReID model catalog for BoxMOT appearance-based trackers.

Model names match BoxMOT's TRAINED_URLS exactly (verified from runtime output).
All appearance-based trackers share the same ReID backend, so all catalog models
are compatible with: botsort, boosttrack, strongsort, deepocsort, hybridsort.

Dataset notes:
  msmt17      — 15-camera multi-scene, best generalisation for real deployments
  market1501  — indoor single-scene benchmark
  dukemtmcreid — indoor multi-camera benchmark
"""

from __future__ import annotations

from typing import Any, Dict, List

APPEARANCE_TRACKERS: frozenset[str] = frozenset(
    {"botsort", "boosttrack", "strongsort", "deepocsort", "hybridsort"}
)

_ALL = sorted(APPEARANCE_TRACKERS)

# ── Curated catalog (names must match BoxMOT TRAINED_URLS keys exactly) ──────
REID_CATALOG: List[Dict[str, Any]] = [
    # ── OSNet family ──────────────────────────────────────────────────────────
    {
        "name": "osnet_x0_25_msmt17.pt",
        "backbone": "OSNet x0.25",
        "dataset": "MSMT17",
        "description": "Lightest & fastest — recommended starting point",
        "size_mb": 3.2,
        "compatible_trackers": _ALL,
    },
    {
        "name": "osnet_x0_5_msmt17.pt",
        "backbone": "OSNet x0.5",
        "dataset": "MSMT17",
        "description": "Balanced speed / accuracy",
        "size_mb": 7.0,
        "compatible_trackers": _ALL,
    },
    {
        "name": "osnet_x0_75_msmt17.pt",
        "backbone": "OSNet x0.75",
        "dataset": "MSMT17",
        "description": "Good accuracy with moderate size",
        "size_mb": 13.0,
        "compatible_trackers": _ALL,
    },
    {
        "name": "osnet_x1_0_msmt17.pt",
        "backbone": "OSNet x1.0",
        "dataset": "MSMT17",
        "description": "Full-size OSNet — standard accuracy benchmark",
        "size_mb": 22.0,
        "compatible_trackers": _ALL,
    },
    {
        "name": "osnet_ibn_x1_0_msmt17.pt",
        "backbone": "OSNet-IBN x1.0",
        "dataset": "MSMT17",
        "description": "Instance-Batch Norm — improved domain generalisation",
        "size_mb": 22.0,
        "compatible_trackers": _ALL,
    },
    {
        "name": "osnet_ain_x1_0_msmt17.pt",
        "backbone": "OSNet-AIN x1.0",
        "dataset": "MSMT17",
        "description": "Attentive Instance Norm — best OSNet accuracy",
        "size_mb": 22.0,
        "compatible_trackers": _ALL,
    },
    # ── MobileNetV2 family ────────────────────────────────────────────────────
    {
        "name": "mobilenetv2_x1_0_msmt17.pt",
        "backbone": "MobileNetV2 x1.0",
        "dataset": "MSMT17",
        "description": "Mobile-friendly, efficient on edge devices",
        "size_mb": 15.0,
        "compatible_trackers": _ALL,
    },
    {
        "name": "mobilenetv2_x1_4_msmt17.pt",
        "backbone": "MobileNetV2 x1.4",
        "dataset": "MSMT17",
        "description": "Wider MobileNetV2 — slightly better accuracy",
        "size_mb": 25.0,
        "compatible_trackers": _ALL,
    },
    # ── CLIP-based ────────────────────────────────────────────────────────────
    {
        "name": "clip_market1501.pt",
        "backbone": "CLIP",
        "dataset": "Market-1501",
        "description": "Vision-language backbone — strong appearance features",
        "size_mb": 150.0,
        "compatible_trackers": _ALL,
    },
    # ── ResNet-50 ─────────────────────────────────────────────────────────────
    {
        "name": "resnet50_msmt17.pt",
        "backbone": "ResNet-50",
        "dataset": "MSMT17",
        "description": "Classic heavy backbone — reliable baseline",
        "size_mb": 95.0,
        "compatible_trackers": _ALL,
    },
    # ── LMBN-N ────────────────────────────────────────────────────────────────
    {
        "name": "lmbn_n_market.pt",
        "backbone": "LMBN-N",
        "dataset": "Market-1501",
        "description": "Lightweight Multi-Branch Network — compact",
        "size_mb": 5.0,
        "compatible_trackers": _ALL,
    },
    # ── HACNN ─────────────────────────────────────────────────────────────────
    {
        "name": "hacnn_msmt17.pt",
        "backbone": "HACNN",
        "dataset": "MSMT17",
        "description": "Harmonious Attention CNN — good for occluded scenes",
        "size_mb": 5.0,
        "compatible_trackers": _ALL,
    },
]

CATALOG_BY_NAME: Dict[str, Dict[str, Any]] = {m["name"]: m for m in REID_CATALOG}


def get_downloadable_names() -> List[str]:
    """Return model names that BoxMOT can actually download (TRAINED_URLS check)."""
    try:
        from boxmot.reid.core.config import TRAINED_URLS
        return [m["name"] for m in REID_CATALOG if m["name"] in TRAINED_URLS]
    except Exception:
        return [m["name"] for m in REID_CATALOG]
