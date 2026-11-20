from __future__ import annotations

from fastapi import Request

from app.data.store import FlightStore


def get_store(request: Request) -> FlightStore:
    """The store is loaded once in the app lifespan and is read-only afterwards."""
    return request.app.state.store
