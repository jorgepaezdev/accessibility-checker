from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = ROOT / "vendor"
VENDOR_AXE = VENDOR_DIR / "axe.min.js"


def axe_core_home() -> Path:
    override = os.environ.get("AXE_CORE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "axe-core").resolve()


def axe_package_json() -> dict:
    package = axe_core_home() / "package.json"
    if not package.exists():
        return {"name": "axe-core", "version": "unknown"}
    return json.loads(package.read_text(encoding="utf-8"))


def axe_version() -> str:
    return str(axe_package_json().get("version") or "unknown")
