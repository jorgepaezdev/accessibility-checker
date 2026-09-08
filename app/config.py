from __future__ import annotations

from typing import Any, Optional

from app.catalog import STANDARD_PRESETS, load_locale, load_rules
from app.models import ConfigureSpec, RunOptions, ScanContext, ScanRequest

UNSAFE_FUNCTION_KEYS = {"evaluate", "after", "matches", "run", "collect", "cleanup"}


def drop_functions(value: Any) -> Any:
    if isinstance(value, list):
        return [drop_functions(item) for item in value]
    if isinstance(value, dict):
        return {
            key: drop_functions(item)
            for key, item in value.items()
            if key not in UNSAFE_FUNCTION_KEYS
        }
    return value


def parse_selector_list(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (list, dict)):
        return raw
    if not isinstance(raw, str):
        return raw
    parts = [part.strip() for part in raw.replace("\r", "\n").split("\n")]
    parts = [part for chunk in parts for part in chunk.split(",") if part.strip()]
    parts = [part.strip() for part in parts if part.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return parts


def build_context(context: Optional[ScanContext]) -> Any:
    if context is None:
        return None
    payload: dict[str, Any] = {}
    include = parse_selector_list(context.include)
    exclude = parse_selector_list(context.exclude)
    if include is not None:
        payload["include"] = include
    if exclude is not None:
        payload["exclude"] = exclude
    if context.from_frames is not None:
        frames = parse_selector_list(context.from_frames)
        payload["fromFrames"] = frames if isinstance(frames, list) else [frames]
    if context.from_shadow_dom is not None:
        shadow = parse_selector_list(context.from_shadow_dom)
        payload["fromShadowDom"] = shadow if isinstance(shadow, list) else [shadow]
    return payload or None


def build_run_options(options: Optional[RunOptions], preset: Optional[str] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if options:
        data = options.model_dump(by_alias=True, exclude_none=True)
        payload.update(data)
    if preset and preset in STANDARD_PRESETS and "runOnly" not in payload:
        tags = STANDARD_PRESETS[preset]["tags"]
        if tags:
            payload["runOnly"] = {"type": "tag", "values": tags}
    return payload


def build_configure(
    configure: Optional[ConfigureSpec],
    locale_id: Optional[str] = None,
    enable_experimental: bool = False,
    preset: Optional[str] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if configure:
        payload.update(drop_functions(configure.model_dump(by_alias=True, exclude_none=True)))
    if locale_id:
        locale = load_locale(locale_id)
        if locale:
            payload["locale"] = locale
    if enable_experimental or preset == "all":
        payload["tagExclude"] = []
        if preset == "all":
            payload["rules"] = payload.get("rules") or [
                {"id": rule["ruleId"], "enabled": True} for rule in load_rules()
            ]
    if "allowedOrigins" not in payload:
        payload["allowedOrigins"] = ["<unsafe_all_origins>"]
    return payload


def build_scan_payload(request: ScanRequest) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    context = build_context(request.context)
    options = build_run_options(request.options, request.preset)
    if request.enable_best_practice is False and options.get("runOnly"):
        run_only = options["runOnly"]
        if isinstance(run_only, dict):
            values = [tag for tag in run_only.get("values", []) if tag != "best-practice"]
            options["runOnly"] = {**run_only, "values": values}
    configure = build_configure(
        request.configure,
        locale_id=request.locale,
        enable_experimental=request.enable_experimental,
        preset=request.preset,
    )
    return context, options, configure
