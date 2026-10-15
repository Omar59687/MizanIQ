"""V0-01A configuration validation tests (synthetic-only, loopback-only)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_default_mode_is_development_demo() -> None:
    settings = Settings()
    assert settings.mode == "development-demo"


def test_rejects_production_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(mode="production")  # type: ignore[arg-type]


def test_rejects_real_world_mode_variants() -> None:
    for bad in ("prod", "staging", "real", "", "DEMO"):
        with pytest.raises(ValidationError):
            Settings(mode=bad)  # type: ignore[arg-type]


def test_mode_is_case_insensitive_but_normalized() -> None:
    settings = Settings(mode="Development-Demo")  # type: ignore[arg-type]
    assert settings.mode == "development-demo"


def test_rejects_public_listeners() -> None:
    for bad_host in ("0.0.0.0", "::", "example.com", "192.168.1.10", ""):
        with pytest.raises(ValidationError):
            Settings(host=bad_host)


def test_allows_loopback_hosts_only() -> None:
    assert Settings(host="127.0.0.1").host == "127.0.0.1"
    assert Settings(host="localhost").host == "localhost"


def test_rejects_unknown_settings_keys() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"mode": "development-demo", "unknown_key": "x"})
