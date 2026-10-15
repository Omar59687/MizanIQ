"""V0-01A configuration: synthetic DEVELOPMENT/DEMO only, loopback only.

Architecture refs: ARCHITECTURE.md sections 2.1-2.2 (synthetic single-operator
DEVELOPMENT/DEMO mode, mode selected in trusted startup configuration, never a
request field); SOFTWARE_FACTORY.md V0 (bounded startup/config, synthetic-mode
isolation, no real-data enablement).

V0-01A scope: validate mode + loopback bind at startup and fail closed on any
non-synthetic or public-listener configuration. HTTPS auth, PostgreSQL tenant
isolation and durable safety journal belong to later V0 packages and are NOT
implemented here.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SYNTHETIC_MODE = "development-demo"
ALLOWED_HOSTS: tuple[str, ...] = ("127.0.0.1", "localhost")
APP_VERSION = "0.1.0"


class Settings(BaseSettings):
    """Trusted startup configuration (environment / .env, never request data)."""

    model_config = SettingsConfigDict(
        env_prefix="MIZANIQ_",
        env_file=".env",
        extra="forbid",
    )

    app_name: str = Field(default="MizanIQ-Next")
    version: str = Field(default=APP_VERSION)
    mode: str = Field(
        default=SYNTHETIC_MODE,
        description="Only synthetic DEVELOPMENT/DEMO is permitted in V0-01A.",
    )
    host: str = Field(
        default="127.0.0.1",
        description="Loopback bind only; public listeners are rejected.",
    )
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator("mode")
    @classmethod
    def _mode_must_be_synthetic(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "development-demo":
            raise ValueError(
                "V0-01A permits only mode='development-demo'; "
                f"got {value!r}. Refusing startup (no real-world enablement)."
            )
        return normalized

    @field_validator("host")
    @classmethod
    def _host_must_be_loopback(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_HOSTS:
            raise ValueError(
                "V0-01A permits only loopback bind "
                f"{list(ALLOWED_HOSTS)}; got {value!r}. Refusing startup."
            )
        # Preserve canonical loopback spelling for 127.0.0.1; keep localhost if given.
        return normalized


def get_settings() -> Settings:
    """Build and validate trusted startup settings; raises on invalid config."""
    return Settings()
