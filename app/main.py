from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from playwright.async_api import Error as PlaywrightError

from app.catalog import catalog, filter_rules, load_rules
from app.engine import ensure_engine
from app.models import InspectRequest, ScanRequest, VirtualRuleRequest
from app.paths import axe_core_home, axe_version
from app.scanner import AxeScanner

STATIC = Path(__file__).resolve().parent / "static"
TEMPLATES = Path(__file__).resolve().parent / "templates"

scanner = AxeScanner()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_engine()
    yield
    await scanner.stop()


app = FastAPI(
    title="Access Scan",
    version="1.0.0",
    description="Website accessibility checker that runs the local axe-core engine.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES))


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "axe_version": axe_version(),
            "axe_home": str(axe_core_home()),
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": f"axe-core {axe_version()}"}


@app.get("/api/catalog")
def get_catalog(locale: Optional[str] = Query(default=None)) -> dict:
    try:
        return catalog(locale)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/rules")
def get_rules(
    tags: Optional[str] = Query(default=None),
    locale: Optional[str] = Query(default=None),
) -> dict:
    from app.catalog import apply_locale_to_rules

    tag_list = [part.strip() for part in (tags or "").split(",") if part.strip()]
    rules = filter_rules(tag_list or None)
    rules = apply_locale_to_rules(rules, locale)
    return {"count": len(rules), "rules": rules}


@app.get("/api/rules/{rule_id}")
def get_rule(rule_id: str) -> dict:
    for rule in load_rules():
        if rule["ruleId"] == rule_id:
            return rule
    raise HTTPException(status_code=404, detail=f"Unknown rule '{rule_id}'.")


@app.post("/api/scan")
async def scan(payload: ScanRequest) -> dict:
    if payload.source.type == "url" and not (payload.source.url or "").strip():
        raise HTTPException(status_code=400, detail="Enter a website URL.")
    if payload.source.type == "html" and not (payload.source.html or "").strip():
        raise HTTPException(status_code=400, detail="Paste HTML to scan.")
    try:
        return await scanner.scan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PlaywrightError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not load or scan the page: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Accessibility scan failed: {exc}",
        ) from exc


@app.post("/api/virtual-rule")
async def virtual_rule(payload: VirtualRuleRequest) -> dict:
    try:
        return await scanner.run_virtual_rule(payload)
    except PlaywrightError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/inspect")
async def inspect(payload: InspectRequest) -> dict:
    try:
        return await scanner.inspect(payload)
    except PlaywrightError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=48731,
        reload=False,
    )


if __name__ == "__main__":
    run()
