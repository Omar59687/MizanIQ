"""V0-01A health-endpoint and safe-startup API tests."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import build_health_payload, create_app


def _client() -> TestClient:
    settings = Settings()
    return TestClient(create_app(settings))


def test_healthz_returns_ok_with_synthetic_marker() -> None:
    response = _client().get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "development-demo"
    assert body["synthetic"] is True
    assert body["version"] == Settings().version


def test_healthz_payload_contains_no_sensitive_keys() -> None:
    body = _client().get("/healthz").json()
    lowered = {str(k).lower() for k in body}
    for forbidden in (
        "password",
        "secret",
        "token",
        "session",
        "credential",
        "fact",
        "ledger",
        "amount",
        "revenue",
        "balance",
    ):
        assert forbidden not in lowered
    raw = str(body).lower()
    assert "password" not in raw
    assert "secret" not in raw


def test_no_business_endpoints_exist() -> None:
    client = _client()
    for path in (
        "/facts",
        "/metrics",
        "/login",
        "/auth",
        "/approve",
        "/upload",
        "/reports",
    ):
        assert client.get(path).status_code == 404


def test_only_healthz_is_application_route() -> None:
    app = create_app(Settings())
    app_paths = sorted({getattr(route, "path", "") for route in app.routes})
    assert "/healthz" in app_paths
    for forbidden in ("/facts", "/login", "/auth", "/metrics"):
        assert forbidden not in app_paths


def test_complete_route_inventory_is_healthz_only() -> None:
    app = create_app(Settings())
    app_paths = sorted({getattr(route, "path", "") for route in app.routes})
    assert app_paths == ["/healthz"]


def test_documentation_endpoints_are_disabled() -> None:
    client = _client()
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_build_app_refuses_non_synthetic_settings_object() -> None:
    bad = Settings()
    object.__setattr__(bad, "mode", "production")
    try:
        create_app(bad)
    except RuntimeError as exc:
        assert "development-demo" in str(exc)
    else:
        raise AssertionError("create_app must refuse non-synthetic mode")


def test_health_payload_builder_is_typed_and_non_sensitive() -> None:
    payload = build_health_payload(Settings())
    assert payload == {
        "status": "ok",
        "mode": "development-demo",
        "version": Settings().version,
        "synthetic": True,
    }
