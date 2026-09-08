import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BROKEN_HTML = """<!doctype html>
<html>
  <body>
    <img src="hero.jpg">
    <button></button>
    <input type="text">
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_scan_html_finds_violations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/scan",
            json={
                "source": {"type": "html", "html": BROKEN_HTML},
                    "preset": "wcag22aa",
                "options": {
                    "iframes": True,
                    "reporter": "v2",
                    "xpath": True,
                    "ancestry": True,
                },
            },
            timeout=60.0,
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    ids = {rule["id"] for rule in payload["results"]["violations"]}
    assert "image-alt" in ids
    assert "button-name" in ids
    assert "html-has-lang" in ids
    assert payload["summary"]["violations"] >= 3
    node = payload["results"]["violations"][0]["nodes"][0]
    assert "xpath" in node
    assert "ancestry" in node


@pytest.mark.asyncio
async def test_virtual_rule_image_alt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/virtual-rule",
            json={
                "ruleId": "image-alt",
                "vNode": {"nodeName": "img", "attributes": {"src": "hero.jpg"}},
            },
            timeout=60.0,
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary"]["violations"] >= 1
    assert payload["results"]["violations"][0]["id"] == "image-alt"


@pytest.mark.asyncio
async def test_commons_inspect():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/inspect",
            json={
                "html": "<!doctype html><html lang='en'><body><button>Save</button></body></html>",
                "selector": "button",
                "calls": ["aria.getRole", "text.accessibleText", "dom.isFocusable"],
            },
            timeout=60.0,
        )
    assert response.status_code == 200, response.text
    values = response.json()["values"]
    assert values["aria.getRole"]["ok"] is True
    assert values["aria.getRole"]["value"] == "button"
    assert values["text.accessibleText"]["ok"] is True
    assert "Save" in str(values["text.accessibleText"]["value"])
    assert values["dom.isFocusable"]["value"] is True
