"""API response models (camelCase JSON) and mapping from domain objects."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.domain.models import Airport, Flight
from app.domain.search import Itinerary, Layover


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AirportOut(ApiModel):
    code: str
    name: str
    city: str
    country: str
    timezone: str

    @classmethod
    def of(cls, a: Airport) -> AirportOut:
        return cls(code=a.code, name=a.name, city=a.city, country=a.country, timezone=a.timezone)


class SegmentOut(ApiModel):
    flight_number: str
    airline: str
    aircraft: str
    origin: AirportOut
    destination: AirportOut
    # Local airport time *with* UTC offset, e.g. "2024-03-15T08:30:00-04:00".
    # The UI should display the wall-clock part as-is, not convert to the browser zone.
    departure_time: str
    arrival_time: str
    duration_minutes: int
    price: float


class LayoverOut(ApiModel):
    airport: AirportOut
    duration_minutes: int
    type: Literal["domestic", "international"]


class ItineraryOut(ApiModel):
    id: str
    stops: int
    total_duration_minutes: int
    total_price: float
    departure_time: str
    arrival_time: str
    segments: list[SegmentOut]
    layovers: list[LayoverOut]


class SearchResponse(ApiModel):
    origin: AirportOut
    destination: AirportOut
    date: date
    count: int
    itineraries: list[ItineraryOut]


class ErrorResponse(ApiModel):
    detail: str
    field: str | None = None


# --------------------------------------------------------------------------- mapping


def _minutes(td: timedelta) -> int:
    return int(td.total_seconds() // 60)


def _money(value: Decimal) -> float:
    # Decimal internally for exact sums; JSON number at the edge for easy display.
    return float(value.quantize(Decimal("0.01")))


def segment_out(f: Flight, airports: dict[str, Airport]) -> SegmentOut:
    return SegmentOut(
        flight_number=f.flight_number,
        airline=f.airline,
        aircraft=f.aircraft,
        origin=AirportOut.of(airports[f.origin]),
        destination=AirportOut.of(airports[f.destination]),
        departure_time=f.departure_local.isoformat(),
        arrival_time=f.arrival_local.isoformat(),
        duration_minutes=_minutes(f.duration),
        price=_money(f.price),
    )


def layover_out(lay: Layover, airports: dict[str, Airport]) -> LayoverOut:
    return LayoverOut(
        airport=AirportOut.of(airports[lay.airport]),
        duration_minutes=_minutes(lay.duration),
        type="domestic" if lay.domestic else "international",
    )


def itinerary_out(it: Itinerary, airports: dict[str, Airport]) -> ItineraryOut:
    return ItineraryOut(
        id="-".join(f.flight_number for f in it.segments),
        stops=it.stops,
        total_duration_minutes=_minutes(it.total_duration),
        total_price=_money(it.total_price),
        departure_time=it.segments[0].departure_local.isoformat(),
        arrival_time=it.segments[-1].arrival_local.isoformat(),
        segments=[segment_out(f, airports) for f in it.segments],
        layovers=[layover_out(lay, airports) for lay in it.layovers],
    )
