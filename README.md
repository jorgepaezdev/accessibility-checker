# Access Scan

Website accessibility checker that runs the **local axe-core** engine from `~/axe-core`.

The app exposes the public axe-core surface in an MVP UI:

- `axe.run` / `axe.runPartial` / `axe.finishRun` for page and iframe testing
- `axe.configure`, `axe.reset`, locales, reporters, checks, rules, and standards
- `axe.getRules` catalog (from `lib/rules` and `lib/checks`)
- `axe.runVirtualRule` for serial virtual nodes
- `axe.setup` / `axe.teardown` plus `axe.commons` inspection
- Context (`include`, `exclude`, `fromFrames`, `fromShadowDom`)
- Run options: tags/presets, `runOnly`, result types, xpath, ancestry, preload, iframes, performance timer

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python3 -m playwright install chromium
python3 -m app
```

Open [http://127.0.0.1:48731](http://127.0.0.1:48731).

If `~/axe-core` is not built, the first launch downloads matching `axe.min.js` (same version as `package.json`, currently 4.13.0) and still reads rules, checks, and locales from the local folder.

Override the engine path with `AXE_CORE_HOME`.

## CLI

```bash
python3 -m app.cli https://example.com --preset wcag22aa
```

Exit code `2` means axe found violations.

## Tests

```bash
pytest -q
```

Scan tests need Playwright Chromium.
