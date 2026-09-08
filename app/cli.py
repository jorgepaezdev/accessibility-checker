from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.engine import ensure_engine
from app.models import ScanRequest, ScanSource
from app.scanner import AxeScanner


async def scan_url(url: str, preset: str, experimental: bool) -> dict:
    ensure_engine()
    scanner = AxeScanner()
    await scanner.start()
    try:
        return await scanner.scan(
            ScanRequest(
                source=ScanSource(type="url", url=url),
                preset=preset,
                enable_experimental=experimental,
            )
        )
    finally:
        await scanner.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a website with the local axe-core engine."
    )
    parser.add_argument("url", help="Website URL to scan")
    parser.add_argument(
        "--preset",
        default="wcag22aa",
        help="Rule preset (wcag22aa, wcag21aa, section508, all, ...)",
    )
    parser.add_argument(
        "--experimental",
        action="store_true",
        help="Include experimental axe-core rules",
    )
    args = parser.parse_args()
    try:
        payload = asyncio.run(scan_url(args.url, args.preset, args.experimental))
    except Exception as exc:  # noqa: BLE001
        print(f"Scan failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(payload, indent=2, default=str))
    summary = payload.get("summary") or {}
    violations = summary.get("violations")
    if isinstance(violations, int) and violations:
        sys.exit(2)


if __name__ == "__main__":
    main()
