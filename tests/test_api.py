import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_home_renders_axe_features(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "Access Scan" in body
    assert "axe-core" in body
    assert "Run accessibility scan" in body
    assert "Virtual rule" in body
    assert "Commons inspector" in body
    assert "Rule catalog" in body
    assert "fromFrames" in body
    assert "performanceTimer" in body


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "axe-core" in response.json()["engine"]


def test_catalog_endpoint(client):
    response = client.get("/api/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"]["version"] == "4.13.0"
    assert len(payload["rules"]) >= 90
    assert payload["presets"]["wcag22aa"]["tags"]


def test_rules_filter(client):
    response = client.get("/api/rules", params={"tags": "wcag2a"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["rules"])
    assert payload["count"] > 0


def test_scan_requires_url(client):
    response = client.post("/api/scan", json={"source": {"type": "url", "url": ""}})
    assert response.status_code == 400


def test_scan_rejects_html_source(client):
    response = client.post(
        "/api/scan",
        json={"source": {"type": "html", "html": "<html></html>"}},
    )
    assert response.status_code == 422
