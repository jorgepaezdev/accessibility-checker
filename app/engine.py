from __future__ import annotations

from pathlib import Path

import httpx

from app.paths import VENDOR_AXE, VENDOR_DIR, axe_core_home, axe_version

AXE_CDN = "https://cdn.jsdelivr.net/npm/axe-core@{version}/axe.min.js"


def engine_path() -> Path:
    home = axe_core_home()
    for name in ("axe.min.js", "axe.js"):
        candidate = home / name
        if candidate.exists():
            return candidate
    return VENDOR_AXE


def engine_source() -> str:
    path = ensure_engine()
    return path.read_text(encoding="utf-8")


def ensure_engine() -> Path:
    path = engine_path()
    if path.exists():
        return path
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    version = axe_version()
    if version == "unknown":
        version = "4.13.0"
    url = AXE_CDN.format(version=version)
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
    return path
