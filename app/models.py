from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Viewport(BaseModel):
    width: int = Field(1280, ge=320, le=3840)
    height: int = Field(720, ge=320, le=2160)
    mobile: bool = False


class ScanSource(BaseModel):
    type: str = Field("url", pattern="^url$")
    url: Optional[str] = Field(None, max_length=4000)


class ScanContext(BaseModel):
    include: Optional[Any] = None
    exclude: Optional[Any] = None
    from_frames: Optional[Any] = Field(None, alias="fromFrames")
    from_shadow_dom: Optional[Any] = Field(None, alias="fromShadowDom")

    model_config = {"populate_by_name": True}


class RunOptions(BaseModel):
    run_only: Optional[Any] = Field(None, alias="runOnly")
    rules: Optional[dict[str, dict[str, Any]]] = None
    reporter: Optional[str] = None
    result_types: Optional[list[str]] = Field(None, alias="resultTypes")
    selectors: Optional[bool] = None
    ancestry: Optional[bool] = None
    xpath: Optional[bool] = None
    absolute_paths: Optional[bool] = Field(None, alias="absolutePaths")
    iframes: Optional[bool] = None
    element_ref: Optional[bool] = Field(None, alias="elementRef")
    frame_wait_time: Optional[int] = Field(None, alias="frameWaitTime", ge=0, le=300000)
    preload: Optional[Any] = None
    performance_timer: Optional[bool] = Field(None, alias="performanceTimer")
    ping_wait_time: Optional[int] = Field(None, alias="pingWaitTime", ge=0, le=60000)

    model_config = {"populate_by_name": True}


class ConfigureSpec(BaseModel):
    branding: Optional[Any] = None
    reporter: Optional[str] = None
    checks: Optional[list[dict[str, Any]]] = None
    rules: Optional[list[dict[str, Any]]] = None
    standards: Optional[dict[str, Any]] = None
    locale: Optional[Any] = None
    axe_version: Optional[str] = Field(None, alias="axeVersion")
    disable_other_rules: Optional[bool] = Field(None, alias="disableOtherRules")
    no_html: Optional[bool] = Field(None, alias="noHtml")
    allowed_origins: Optional[list[str]] = Field(None, alias="allowedOrigins")
    tag_exclude: Optional[list[str]] = Field(None, alias="tagExclude")

    model_config = {"populate_by_name": True}


class ScanRequest(BaseModel):
    source: ScanSource
    context: Optional[ScanContext] = None
    options: Optional[RunOptions] = None
    configure: Optional[ConfigureSpec] = None
    locale: Optional[str] = Field(None, max_length=16)
    preset: Optional[str] = Field(None, max_length=64)
    enable_experimental: bool = Field(False, alias="enableExperimental")
    enable_best_practice: Optional[bool] = Field(None, alias="enableBestPractice")
    viewport: Viewport = Field(default_factory=Viewport)
    timeout_ms: int = Field(30000, ge=1000, le=120000, alias="timeoutMs")
    wait_until: str = Field("load", alias="waitUntil", pattern="^(load|domcontentloaded|networkidle|commit)$")
    element_internals: Optional[list[dict[str, Any]]] = Field(None, alias="elementInternals")
    element_internals_timeout: Optional[int] = Field(
        None, alias="elementInternalsTimeout", ge=0, le=30000
    )

    model_config = {"populate_by_name": True}


class VirtualNodeSpec(BaseModel):
    node_name: str = Field(..., alias="nodeName", min_length=1, max_length=100)
    attributes: dict[str, Any] = Field(default_factory=dict)
    children: Optional[list[dict[str, Any]]] = None
    node_type: Optional[int] = Field(None, alias="nodeType")
    node_value: Optional[str] = Field(None, alias="nodeValue")

    model_config = {"populate_by_name": True}


class VirtualRuleRequest(BaseModel):
    rule_id: str = Field(..., alias="ruleId", min_length=1, max_length=120)
    v_node: VirtualNodeSpec = Field(..., alias="vNode")
    options: Optional[RunOptions] = None
    configure: Optional[ConfigureSpec] = None
    locale: Optional[str] = Field(None, max_length=16)

    model_config = {"populate_by_name": True}


class InspectRequest(BaseModel):
    html: str = Field(..., min_length=1, max_length=500_000)
    selector: str = Field(..., min_length=1, max_length=1000)
    calls: list[str] = Field(default_factory=list)
    locale: Optional[str] = Field(None, max_length=16)

    model_config = {"populate_by_name": True}
