from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

from app.paths import ROOT, axe_version

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright-browsers"))

from playwright.async_api import async_playwright
from playwright.async_api import Error as PlaywrightError

from app.engine import engine_source
from app.models import InspectRequest, ScanRequest, VirtualRuleRequest
from app.config import build_scan_payload

LAUNCH_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
]


INJECT_AND_CONFIGURE = """
({ spec }) => {
  if (typeof axe === 'undefined') {
    throw new Error('axe-core did not load in this frame');
  }
  if (typeof axe.reset === 'function') {
    axe.reset();
  }
  if (spec && Object.keys(spec).length) {
    axe.configure(spec);
  }
}
"""

COLLECT_PARTIAL = """
async ({ context, options }) => {
  const ctx = context == null ? document : context;
  const frameContexts = axe.utils.getFrameContexts(ctx, options || {});
  const partial = await axe.runPartial(ctx, options || {});
  return { partial, frameContexts };
}
"""

FINISH_RUN = """
async ({ partialResults, options }) => {
  return await axe.finishRun(partialResults, options || {});
}
"""

RUN_TOP = """
async ({ context, options }) => {
  const ctx = context == null ? document : context;
  return await axe.run(ctx, options || {});
}
"""

RUN_VIRTUAL = """
({ ruleId, vNode, options, spec }) => {
  if (typeof axe.reset === 'function') axe.reset();
  if (spec && Object.keys(spec).length) axe.configure(spec);
  return axe.runVirtualRule(ruleId, vNode, options || {});
}
"""

INSPECT_COMMONS = """
({ selector, calls }) => {
  const serialize = (value, seen) => {
    if (value == null) return value;
    if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'string') {
      return value;
    }
    if (typeof value === 'function') return '[Function]';
    if (value instanceof Error) {
      return { name: value.name, message: value.message };
    }
    if (typeof Node !== 'undefined' && value instanceof Node) {
      const el = value.nodeType === 1 ? value : value.parentElement;
      return {
        nodeName: value.nodeName,
        html: el && el.outerHTML ? el.outerHTML.slice(0, 500) : null,
      };
    }
    if (typeof value.toJSON === 'function') {
      try { return value.toJSON(); } catch (err) { /* continue */ }
    }
    if (value && typeof value.red === 'number' && typeof value.green === 'number') {
      return {
        hex: typeof value.toHexString === 'function' ? value.toHexString() : undefined,
        red: value.red,
        green: value.green,
        blue: value.blue,
        alpha: value.alpha,
      };
    }
    if (seen.has(value)) return '[Circular]';
    if (Array.isArray(value)) {
      seen.add(value);
      return value.slice(0, 50).map((item) => serialize(item, seen));
    }
    if (typeof value === 'object') {
      seen.add(value);
      const out = {};
      for (const [key, item] of Object.entries(value)) {
        if (out && Object.keys(out).length > 40) break;
        out[key] = serialize(item, seen);
      }
      return out;
    }
    return String(value);
  };

  axe.setup(document);
  try {
    const el = document.querySelector(selector);
    if (!el) {
      throw new Error('No element matched selector: ' + selector);
    }
    const results = {};
    for (const call of calls) {
      const parts = String(call).split('.');
      let fn = axe.commons;
      for (const part of parts) {
        fn = fn && fn[part];
      }
      if (typeof fn !== 'function') {
        results[call] = { error: 'Not a function on axe.commons' };
        continue;
      }
      try {
        results[call] = { ok: true, value: serialize(fn(el), new Set()) };
      } catch (err) {
        results[call] = { ok: false, error: err && err.message ? err.message : String(err) };
      }
    }
    return results;
  } finally {
    axe.teardown();
  }
}
"""

EXTERNAL_APIS = """
({ internals, timeout }) => {
  const spec = {};
  if (timeout != null) spec.elementInternalsTimeout = timeout;
  if (internals) {
    spec.elementInternals = () => Promise.resolve(internals);
  }
  if (Object.keys(spec).length) {
    axe.externalAPIs(spec);
  }
}
"""


class AxeScanner:
    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    @asynccontextmanager
    async def _session(self, viewport: dict[str, int], timeout_ms: int):
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=LAUNCH_ARGS,
            chromium_sandbox=False,
        )
        page = await browser.new_page(viewport=viewport)
        page.set_default_timeout(timeout_ms)
        try:
            yield browser, page
        finally:
            await page.close()
            await browser.close()
            await playwright.stop()

    async def _inject(self, page_or_frame: Any, spec: dict[str, Any]) -> None:
        source = engine_source()
        await page_or_frame.add_script_tag(content=source)
        await page_or_frame.evaluate(INJECT_AND_CONFIGURE, {"spec": spec})

    async def _collect_partials(
        self,
        frame: Any,
        context: Any,
        options: dict[str, Any],
        spec: dict[str, Any],
    ) -> list[Any]:
        try:
            await self._inject(frame, spec)
        except PlaywrightError:
            return [None]

        try:
            collected = await frame.evaluate(
                COLLECT_PARTIAL, {"context": context, "options": options}
            )
        except PlaywrightError:
            return [None]

        partial = collected.get("partial")
        frame_contexts = collected.get("frameContexts") or []
        results = [partial]
        if partial is None:
            return results

        for item in frame_contexts:
            selector = item.get("frameSelector")
            child_context = item.get("frameContext")
            child = await self._child_frame(frame, selector)
            if child is None:
                results.append(None)
                continue
            results.extend(
                await self._collect_partials(child, child_context, options, spec)
            )
        return results

    async def _child_frame(self, frame: Any, selector: Any) -> Any:
        try:
            handle = await frame.evaluate_handle(
                """(sel) => {
                  if (typeof axe !== 'undefined' && axe.utils && axe.utils.shadowSelect) {
                    return axe.utils.shadowSelect(sel);
                  }
                  if (typeof sel === 'string') return document.querySelector(sel);
                  return null;
                }""",
                selector,
            )
            element = handle.as_element()
            if element is None:
                return None
            return await element.content_frame()
        except PlaywrightError:
            return None

    async def scan(self, request: ScanRequest) -> dict[str, Any]:
        context, options, spec = build_scan_payload(request)
        async with self._session(
            {"width": request.viewport.width, "height": request.viewport.height},
            request.timeout_ms,
        ) as (browser, page):
            logs: list[str] = []
            page.on("console", lambda msg: logs.append(f"{msg.type}: {msg.text}"))

            if request.source.type == "html":
                html = request.source.html or ""
                await page.set_content(html, wait_until=request.wait_until)
            else:
                url = (request.source.url or "").strip()
                if not url:
                    raise ValueError("Enter a website URL.")
                if "://" not in url:
                    url = "https://" + url
                await page.goto(url, wait_until=request.wait_until, timeout=request.timeout_ms)

            if request.element_internals is not None or request.element_internals_timeout is not None:
                await self._inject(page, spec)
                await page.evaluate(
                    EXTERNAL_APIS,
                    {
                        "internals": request.element_internals,
                        "timeout": request.element_internals_timeout,
                    },
                )

            use_partial = options.get("iframes", True)
            if use_partial:
                partials = await self._collect_partials(page, context, options, spec)
                blank = await browser.new_page()
                try:
                    await blank.add_script_tag(content=engine_source())
                    results = await blank.evaluate(
                        FINISH_RUN,
                        {"partialResults": partials, "options": options},
                    )
                finally:
                    await blank.close()
            else:
                await self._inject(page, spec)
                results = await page.evaluate(
                    RUN_TOP, {"context": context, "options": options}
                )

            return {
                "engine": {"name": "axe-core", "version": axe_version()},
                "source": {
                    "type": request.source.type,
                    "url": page.url,
                },
                "context": context,
                "options": options,
                "configure": _public_configure(spec),
                "performanceLogs": logs if options.get("performanceTimer") else [],
                "results": results,
                "summary": summarize(results),
            }

    async def run_virtual_rule(self, request: VirtualRuleRequest) -> dict[str, Any]:
        from app.config import build_configure, build_run_options

        spec = build_configure(request.configure, locale_id=request.locale)
        options = build_run_options(request.options)
        v_node = request.v_node.model_dump(by_alias=True, exclude_none=True)
        async with self._session({"width": 800, "height": 600}, 15000) as (_browser, page):
            await page.set_content("<!doctype html><html><body></body></html>")
            await page.add_script_tag(content=engine_source())
            results = await page.evaluate(
                RUN_VIRTUAL,
                {
                    "ruleId": request.rule_id,
                    "vNode": v_node,
                    "options": options,
                    "spec": spec,
                },
            )
            return {
                "engine": {"name": "axe-core", "version": axe_version()},
                "ruleId": request.rule_id,
                "vNode": v_node,
                "results": results,
                "summary": summarize(results),
            }

    async def inspect(self, request: InspectRequest) -> dict[str, Any]:
        from app.config import build_configure
        from app.catalog import COMMONS_CALLS

        spec = build_configure(None, locale_id=request.locale)
        allowed = {item["id"] for item in COMMONS_CALLS}
        calls = [call for call in request.calls if call in allowed]
        if not calls:
            calls = [item["id"] for item in COMMONS_CALLS]
        async with self._session({"width": 800, "height": 600}, 15000) as (_browser, page):
            await page.set_content(request.html, wait_until="load")
            await self._inject(page, spec)
            values = await page.evaluate(
                INSPECT_COMMONS, {"selector": request.selector, "calls": calls}
            )
            return {
                "engine": {"name": "axe-core", "version": axe_version()},
                "selector": request.selector,
                "calls": calls,
                "values": values,
            }


def _public_configure(spec: dict[str, Any]) -> dict[str, Any]:
    public = dict(spec)
    if isinstance(public.get("locale"), dict):
        public["locale"] = public["locale"].get("lang")
    return public


def summarize(results: Any) -> dict[str, Any]:
    if isinstance(results, dict) and "violations" in results:
        groups = {
            "violations": results.get("violations") or [],
            "incomplete": results.get("incomplete") or [],
            "passes": results.get("passes") or [],
            "inapplicable": results.get("inapplicable") or [],
        }
        impact_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
        for rule in groups["violations"]:
            impact = (rule or {}).get("impact") or "minor"
            if impact in impact_counts:
                impact_counts[impact] += 1
        return {
            "violations": len(groups["violations"]),
            "incomplete": len(groups["incomplete"]),
            "passes": len(groups["passes"]),
            "inapplicable": len(groups["inapplicable"]),
            "impact": impact_counts,
            "url": results.get("url"),
            "timestamp": results.get("timestamp"),
            "testEngine": results.get("testEngine"),
            "testEnvironment": results.get("testEnvironment"),
            "testRunner": results.get("testRunner"),
        }
    if isinstance(results, list):
        return {"rawCount": len(results)}
    if isinstance(results, dict) and "rawArray" in results:
        return {"rawCount": len(results.get("rawArray") or [])}
    return {"raw": True}


def results_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)
