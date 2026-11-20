from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_store
from app.data.store import FlightStore
from app.domain.search import (
    SameAirportError,
    UnknownAirportError,
    search_itineraries,
)
from app.schemas.search import AirportOut, ErrorResponse, SearchResponse, itinerary_out

router = APIRouter()

Store = Annotated[FlightStore, Depends(get_store)]
IataCode = Annotated[
    str,
    Query(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
        description="3-letter IATA airport code (case-insensitive)",
        examples=["JFK"],
    ),
]


@router.get("/health", tags=["meta"])
def health(store: Store) -> dict[str, Any]:
    return {"status": "ok", "airports": len(store.airports), "flights": store.flight_count}


@router.get("/api/airports", response_model=list[AirportOut], tags=["airports"])
def list_airports(store: Store) -> list[AirportOut]:
    return [AirportOut.of(a) for a in sorted(store.airports.values(), key=lambda a: a.code)]


@router.get("/api/data-quality", tags=["meta"])
def data_quality(store: Store) -> dict[str, Any]:
    """What the loader dropped or coerced from the raw dataset, and why."""
    return store.report.to_dict()


@router.get(
    "/api/search",
    response_model=SearchResponse,
    response_model_by_alias=True,
    tags=["search"],
    responses={400: {"model": ErrorResponse}},
)
def search(
    store: Store,
    origin: IataCode,
    destination: IataCode,
    date: Annotated[date, Query(description="Local departure date at origin (YYYY-MM-DD)")],
) -> SearchResponse:
    origin, destination = origin.upper(), destination.upper()
    try:
        itineraries = search_itineraries(store, origin, destination, date)
    except UnknownAirportError as exc:
        field = "origin" if exc.code == origin else "destination"
        raise HTTPException(status_code=400, detail={"detail": str(exc), "field": field}) from exc
    except SameAirportError as exc:
        raise HTTPException(
            status_code=400, detail={"detail": str(exc), "field": "destination"}
        ) from exc

    return SearchResponse(
        origin=AirportOut.of(store.airports[origin]),
        destination=AirportOut.of(store.airports[destination]),
        date=date,
        count=len(itineraries),
        itineraries=[itinerary_out(it, store.airports) for it in itineraries],
    )
