"""Itinerary search: depth-limited DFS over flights, using a time window per hub.

See README "Tradeoffs considered" for why a bounded DFS was chosen over Dijkstra / CSA / SQL joins.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.data.store import FlightStore
from app.domain.models import Flight
from app.domain.rules import (
    MAX_LAYOVER,
    MAX_SEGMENTS,
    SMALLEST_MIN_LAYOVER,
    is_domestic_connection,
    min_layover,
)


class SearchError(ValueError):
    """Invalid search request (business-rule level, not shape level)."""


class UnknownAirportError(SearchError):
    def __init__(self, code: str):
        super().__init__(f"Unknown airport code: {code}")
        self.code = code


class SameAirportError(SearchError):
    def __init__(self) -> None:
        super().__init__("Origin and destination must differ")


@dataclass(frozen=True)
class Layover:
    airport: str
    duration: timedelta
    domestic: bool


@dataclass(frozen=True)
class Itinerary:
    segments: tuple[Flight, ...]
    layovers: tuple[Layover, ...]

    @property
    def total_duration(self) -> timedelta:
        # UTC on both ends, so date-line and DST cases are correct by construction.
        return self.segments[-1].arrival_utc - self.segments[0].departure_utc

    @property
    def total_price(self) -> Decimal:
        return sum((f.price for f in self.segments), Decimal("0")).quantize(Decimal("0.01"))

    @property
    def stops(self) -> int:
        return len(self.segments) - 1

    @property
    def departure_utc(self) -> datetime:
        return self.segments[0].departure_utc


def _build_itinerary(path: list[Flight], store: FlightStore) -> Itinerary:
    layovers = tuple(
        Layover(
            airport=arriving.destination,
            duration=departing.departure_utc - arriving.arrival_utc,
            domestic=is_domestic_connection(arriving, departing, store.airports),
        )
        for arriving, departing in zip(path, path[1:], strict=False)
    )
    return Itinerary(segments=tuple(path), layovers=layovers)


def _sort_key(it: Itinerary) -> tuple:
    # Spec: shortest total travel time first. Ties: cheaper, then earlier, then
    # flight numbers so the order is fully deterministic.
    return (
        it.total_duration,
        it.total_price,
        it.departure_utc,
        tuple(f.flight_number for f in it.segments),
    )


def validate_request(store: FlightStore, origin: str, destination: str) -> None:
    for code in (origin, destination):
        if code not in store.airports:
            raise UnknownAirportError(code)
    if origin == destination:
        raise SameAirportError()


def search_itineraries(
    store: FlightStore,
    origin: str,
    destination: str,
    travel_date: date,
    max_segments: int = MAX_SEGMENTS,
) -> list[Itinerary]:
    """All valid itineraries from `origin` to `destination` departing on `travel_date`.

    `travel_date` is the *local* calendar date at the origin airport of the first
    segment; later segments may depart on following days (overnight connections).
    """
    validate_request(store, origin, destination)
    results: list[Itinerary] = []

    def candidates(hub: str, arrived_at: datetime) -> list[Flight]:
        """Flights leaving `hub` within [arrival + smallest minimum, arrival + max]."""
        times = store.departure_times_by_airport.get(hub, [])
        lo = bisect_left(times, arrived_at + SMALLEST_MIN_LAYOVER)
        hi = bisect_right(times, arrived_at + MAX_LAYOVER)
        return store.departures_by_airport[hub][lo:hi] if lo < hi else []

    def dfs(path: list[Flight], visited: set[str]) -> None:
        last = path[-1]
        if last.destination == destination:
            results.append(_build_itinerary(path, store))
            return  # never fly *through* the destination and come back
        if len(path) == max_segments:
            return
        # Next flight must leave from the very airport we landed at (exact code),
        # so a JFK -> LGA "connection" can never be generated.
        for nxt in candidates(last.destination, last.arrival_utc):
            if nxt.destination in visited:  # no loops, never return to origin
                continue
            layover = nxt.departure_utc - last.arrival_utc
            if layover < min_layover(last, nxt, store.airports):
                continue  # e.g. 60 min is fine domestic, too short international
            path.append(nxt)
            visited.add(nxt.destination)
            dfs(path, visited)
            visited.discard(nxt.destination)
            path.pop()

    for first in store.departures_by_airport.get(origin, []):
        if first.departure_local.date() == travel_date:
            dfs([first], {origin, first.destination})

    results.sort(key=_sort_key)
    return results
