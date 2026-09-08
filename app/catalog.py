from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.paths import axe_core_home, axe_version

TAG_EXCLUDE_DEFAULT = ("experimental", "deprecated")

STANDARD_PRESETS: dict[str, dict[str, Any]] = {
    "wcag22aa": {
        "label": "WCAG 2.2 AA",
        "tags": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
        "description": "WCAG 2.0/2.1/2.2 Level A and AA (axe-core default-style coverage).",
    },
    "wcag21aa": {
        "label": "WCAG 2.1 AA",
        "tags": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
        "description": "WCAG 2.0 and 2.1 Level A and AA.",
    },
    "wcag2aa": {
        "label": "WCAG 2.0 AA",
        "tags": ["wcag2a", "wcag2aa"],
        "description": "WCAG 2.0 Level A and AA.",
    },
    "wcag2a": {
        "label": "WCAG 2.0 A",
        "tags": ["wcag2a"],
        "description": "WCAG 2.0 Level A only.",
    },
    "wcag2aaa": {
        "label": "WCAG 2.0 AAA",
        "tags": ["wcag2a", "wcag2aa", "wcag2aaa"],
        "description": "WCAG 2.0 through Level AAA.",
    },
    "best-practice": {
        "label": "Best practices",
        "tags": ["best-practice"],
        "description": "Common accessibility best practices that are not WCAG failures.",
    },
    "section508": {
        "label": "Section 508",
        "tags": ["section508"],
        "description": "Legacy US Section 508 requirements.",
    },
    "EN-301-549": {
        "label": "EN 301 549",
        "tags": ["EN-301-549"],
        "description": "European accessibility standard EN 301 549.",
    },
    "RGAAv4": {
        "label": "RGAA v4",
        "tags": ["RGAAv4"],
        "description": "French RGAA v4 requirements.",
    },
    "TTv5": {
        "label": "Trusted Tester v5",
        "tags": ["TTv5"],
        "description": "Trusted Tester v5 rules.",
    },
    "ACT": {
        "label": "W3C ACT",
        "tags": ["ACT"],
        "description": "W3C Accessibility Conformance Testing rules.",
    },
    "experimental": {
        "label": "Experimental",
        "tags": ["experimental"],
        "description": "Cutting-edge rules disabled by default in axe-core.",
    },
    "all": {
        "label": "All rules",
        "tags": [],
        "description": "Every rule in the engine, including experimental and deprecated.",
    },
}

AXE_TAGS = [
    {"id": "wcag2a", "label": "WCAG 2.0 Level A"},
    {"id": "wcag2aa", "label": "WCAG 2.0 Level AA"},
    {"id": "wcag2aaa", "label": "WCAG 2.0 Level AAA"},
    {"id": "wcag21a", "label": "WCAG 2.1 Level A"},
    {"id": "wcag21aa", "label": "WCAG 2.1 Level AA"},
    {"id": "wcag22aa", "label": "WCAG 2.2 Level AA"},
    {"id": "wcag2a-obsolete", "label": "WCAG 2.0 A (obsolete)"},
    {"id": "best-practice", "label": "Best practices"},
    {"id": "experimental", "label": "Experimental"},
    {"id": "ACT", "label": "W3C ACT"},
    {"id": "section508", "label": "Section 508"},
    {"id": "TTv5", "label": "Trusted Tester v5"},
    {"id": "EN-301-549", "label": "EN 301 549"},
    {"id": "RGAAv4", "label": "RGAA v4"},
    {"id": "cat.aria", "label": "Category: ARIA"},
    {"id": "cat.color", "label": "Category: Color"},
    {"id": "cat.forms", "label": "Category: Forms"},
    {"id": "cat.keyboard", "label": "Category: Keyboard"},
    {"id": "cat.language", "label": "Category: Language"},
    {"id": "cat.name-role-value", "label": "Category: Name, role, value"},
    {"id": "cat.parsing", "label": "Category: Parsing"},
    {"id": "cat.semantics", "label": "Category: Semantics"},
    {"id": "cat.sensory-and-visual-cues", "label": "Category: Sensory and visual cues"},
    {"id": "cat.structure", "label": "Category: Structure"},
    {"id": "cat.tables", "label": "Category: Tables"},
    {"id": "cat.text-alternatives", "label": "Category: Text alternatives"},
    {"id": "cat.time-and-media", "label": "Category: Time and media"},
]

REPORTERS = [
    {"id": "v2", "label": "v2 (default)", "description": "Current axe-core result format."},
    {"id": "v1", "label": "v1", "description": "Previous result format, including failureSummary."},
    {"id": "no-passes", "label": "no-passes", "description": "Violations only; omits passing nodes."},
    {"id": "raw", "label": "raw", "description": "Unformatted rule results."},
    {"id": "rawEnv", "label": "rawEnv", "description": "Raw results plus environment data."},
]

LOCALE_LABELS = {
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "es": "Spanish",
    "eu": "Basque",
    "fr": "French",
    "he": "Hebrew",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nb": "Norwegian Bokmål",
    "nl": "Dutch",
    "pl": "Polish",
    "pt_BR": "Portuguese (Brazil)",
    "pt_PT": "Portuguese (Portugal)",
    "ru": "Russian",
    "sv": "Swedish",
    "zh_CN": "Chinese (Simplified)",
    "zh_TW": "Chinese (Traditional)",
}

RESULT_TYPES = ["violations", "incomplete", "passes", "inapplicable"]

COMMONS_CALLS = [
    {"id": "aria.getRole", "label": "ARIA role", "group": "aria"},
    {"id": "aria.getExplicitRole", "label": "Explicit ARIA role", "group": "aria"},
    {"id": "aria.getImplicitRole", "label": "Implicit ARIA role", "group": "aria"},
    {"id": "aria.requiredAttr", "label": "Required ARIA attributes", "group": "aria"},
    {"id": "aria.allowedAttr", "label": "Allowed ARIA attributes", "group": "aria"},
    {"id": "aria.label", "label": "ARIA label", "group": "aria"},
    {"id": "text.accessibleText", "label": "Accessible name", "group": "text"},
    {"id": "text.label", "label": "Label text", "group": "text"},
    {"id": "text.visible", "label": "Visible text", "group": "text"},
    {"id": "text.titleText", "label": "Title text", "group": "text"},
    {"id": "dom.isVisible", "label": "Is visible", "group": "dom"},
    {"id": "dom.isVisibleOnScreen", "label": "Visible on screen", "group": "dom"},
    {"id": "dom.isVisibleToScreenReaders", "label": "Visible to screen readers", "group": "dom"},
    {"id": "dom.isFocusable", "label": "Is focusable", "group": "dom"},
    {"id": "dom.isInTabOrder", "label": "In tab order", "group": "dom"},
    {"id": "dom.isHiddenForEveryone", "label": "Hidden for everyone", "group": "dom"},
    {"id": "dom.getElementCoordinates", "label": "Element coordinates", "group": "dom"},
    {"id": "dom.getTargetSize", "label": "Target size", "group": "dom"},
    {"id": "color.getForegroundColor", "label": "Foreground color", "group": "color"},
    {"id": "color.getBackgroundColor", "label": "Background color", "group": "color"},
    {"id": "forms.isAriaCombobox", "label": "Is ARIA combobox", "group": "forms"},
    {"id": "table.isDataTable", "label": "Is data table", "group": "table"},
]

PUBLIC_APIS = [
    "axe.run",
    "axe.configure",
    "axe.reset",
    "axe.resetLocale",
    "axe.getRules",
    "axe.runPartial",
    "axe.finishRun",
    "axe.runVirtualRule",
    "axe.setup",
    "axe.teardown",
    "axe.cleanup",
    "axe.registerPlugin",
    "axe.frameMessenger",
    "axe.externalAPIs",
    "axe.hasReporter",
    "axe.getReporter",
    "axe.addReporter",
    "axe.utils.querySelectorAll",
    "axe.utils.getRule",
    "axe.utils.getFrameContexts",
    "axe.commons.*",
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_rules() -> list[dict[str, Any]]:
    rules_dir = axe_core_home() / "lib" / "rules"
    rules: list[dict[str, Any]] = []
    if not rules_dir.exists():
        return rules
    for path in sorted(rules_dir.glob("*.json")):
        data = _read_json(path)
        tags = list(data.get("tags") or [])
        enabled = not any(tag in TAG_EXCLUDE_DEFAULT for tag in tags)
        metadata = data.get("metadata") or {}
        rules.append(
            {
                "ruleId": data.get("id", path.stem),
                "impact": data.get("impact"),
                "selector": data.get("selector", "*"),
                "tags": tags,
                "actIds": data.get("actIds") or [],
                "description": metadata.get("description", ""),
                "help": metadata.get("help", ""),
                "enabled": enabled,
                "reviewOnFail": bool(data.get("reviewOnFail")),
                "any": data.get("any") or [],
                "all": data.get("all") or [],
                "none": data.get("none") or [],
                "matches": data.get("matches"),
                "helpUrl": (
                    f"https://dequeuniversity.com/rules/axe/{axe_version()}/"
                    f"{data.get('id', path.stem)}?application=axeAPI"
                ),
            }
        )
    return rules


@lru_cache(maxsize=1)
def load_checks() -> list[dict[str, Any]]:
    checks_dir = axe_core_home() / "lib" / "checks"
    checks: list[dict[str, Any]] = []
    if not checks_dir.exists():
        return checks
    for path in sorted(checks_dir.glob("**/*.json")):
        data = _read_json(path)
        metadata = data.get("metadata") or {}
        checks.append(
            {
                "id": data.get("id", path.stem),
                "evaluate": data.get("evaluate"),
                "after": data.get("after"),
                "options": data.get("options"),
                "impact": metadata.get("impact"),
                "messages": metadata.get("messages"),
                "category": path.parent.name,
            }
        )
    return checks


@lru_cache(maxsize=1)
def available_locales() -> list[dict[str, str]]:
    locales_dir = axe_core_home() / "locales"
    locales = [{"id": "en", "label": "English (default)"}]
    if not locales_dir.exists():
        return locales
    for path in sorted(locales_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        locale_id = path.stem
        locales.append({"id": locale_id, "label": LOCALE_LABELS.get(locale_id, locale_id)})
    return locales


def load_locale(locale_id: str) -> Optional[dict[str, Any]]:
    if not locale_id or locale_id == "en":
        return None
    path = axe_core_home() / "locales" / f"{locale_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown locale '{locale_id}'.")
    return _read_json(path)


def apply_locale_to_rules(rules: list[dict[str, Any]], locale_id: Optional[str]) -> list[dict[str, Any]]:
    locale = load_locale(locale_id) if locale_id else None
    if not locale:
        return rules
    translated = []
    locale_rules = locale.get("rules") or {}
    for rule in rules:
        copy = dict(rule)
        messages = locale_rules.get(rule["ruleId"]) or {}
        if messages.get("description"):
            copy["description"] = messages["description"]
        if messages.get("help"):
            copy["help"] = messages["help"]
        translated.append(copy)
    return translated


def filter_rules(tags: Optional[list[str]] = None) -> list[dict[str, Any]]:
    rules = load_rules()
    if not tags:
        return rules
    wanted = set(tags)
    return [rule for rule in rules if wanted.intersection(rule["tags"])]


def catalog(locale_id: Optional[str] = None) -> dict[str, Any]:
    rules = apply_locale_to_rules(load_rules(), locale_id)
    return {
        "engine": {
            "name": "axe-core",
            "version": axe_version(),
            "home": str(axe_core_home()),
        },
        "presets": STANDARD_PRESETS,
        "tags": AXE_TAGS,
        "reporters": REPORTERS,
        "resultTypes": RESULT_TYPES,
        "locales": available_locales(),
        "commons": COMMONS_CALLS,
        "publicApis": PUBLIC_APIS,
        "standards": ["ariaAttrs", "ariaRoles", "htmlElms", "cssColors"],
        "preloadAssets": ["cssom", "media"],
        "rules": rules,
        "checks": [
            {
                "id": check["id"],
                "category": check["category"],
                "impact": check["impact"],
                "hasOptions": check["options"] is not None,
                "options": check["options"],
            }
            for check in load_checks()
        ],
    }
