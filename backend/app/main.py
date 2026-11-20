"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.data.store import FlightStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_FRIENDLY_FIELD_ERRORS = {
    "origin": "Origin must be a 3-letter airport code (e.g. JFK)",
    "destination": "Destination must be a 3-letter airport code (e.g. LAX)",
    "date": "Date must be a valid date in YYYY-MM-DD format",
}


def create_app(settings: Settings | None = None, store: FlightStore | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Load once at startup; a bad/missing file fails fast instead of on first request.
        app.state.store = store or FlightStore.from_file(settings.data_path)
        logger.info("Store ready: %s", app.state.store.report.summary())
        yield

    app = FastAPI(
        title="SkyPath Flight Search",
        version="0.1.0",
        description="Search direct, 1-stop and 2-stop itineraries over a fixed schedule.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        # Flatten {"detail": {"detail": ..., "field": ...}} into a single error shape.
        body = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Same {detail, field} shape as 400s, with a human message the UI can show as-is.
        errors = []
        for err in exc.errors():
            loc = err.get("loc", ())
            field = str(loc[-1]) if loc else None
            message = _FRIENDLY_FIELD_ERRORS.get(field or "", err.get("msg", "Invalid request"))
            if err.get("type") == "missing":
                message = f"{(field or 'parameter').capitalize()} is required"
            errors.append({"field": field, "detail": message})
        first = errors[0] if errors else {"field": None, "detail": "Invalid request"}
        return JSONResponse(status_code=422, content={**first, "errors": errors})

    app.include_router(router)
    return app


app = create_app()
