"""V0-01A minimal typed FastAPI scaffold.

Exposes exactly one unprotected, non-sensitive endpoint: GET /healthz.
No business endpoints, no credentials, no financial records, no public
listener configuration. Safe startup refuses non-synthetic mode.

Architecture refs: ARCHITECTURE.md sections 2.1-2.2; SOFTWARE_FACTORY.md V0.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, TypedDict

from fastapi import FastAPI

from app.config import APP_VERSION, Settings, get_settings


class HealthPayload(TypedDict):
    status: str
    mode: str
    version: str
    synthetic: bool


def build_health_payload(settings: Settings) -> HealthPayload:
    """Return the non-sensitive health payload (no secrets, no records)."""
    return {
        "status": "ok",
        "mode": settings.mode,
        "version": settings.version,
        "synthetic": True,
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fail closed when trusted startup config is not synthetic/loopback."""
    raw: Any = app.state.settings
    settings = raw if isinstance(raw, Settings) else get_settings()
    if settings.mode != "development-demo":
        raise RuntimeError("Refusing startup: not in synthetic development-demo mode.")
    if settings.host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("Refusing startup: non-loopback host.")
    app.state.settings = settings
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the V0-01A FastAPI application with health endpoint only."""
    resolved: Settings = settings if settings is not None else get_settings()
    # Constructor itself validates (pydantic); double-guard synthetics here.
    if resolved.mode != "development-demo":
        raise RuntimeError("Refusing to build app outside development-demo mode.")

    app = FastAPI(
        title="MizanIQ-Next (V0-01A synthetic foundation)",
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved

    @app.get("/healthz", response_model=None)
    def healthz() -> HealthPayload:
        current: Any = app.state.settings
        active: Settings = current if isinstance(current, Settings) else resolved
        return build_health_payload(active)

    return app


app: FastAPI = create_app()


if __name__ == "__main__":  # pragma: no cover - manual local run only
    import uvicorn

    startup_settings: Settings = get_settings()
    # Hardcoded loopback bind: never 0.0.0.0, never public.
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=startup_settings.port,
        log_level="info",
    )
