"""Connection rules from the spec, in one place."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

from app.domain.models import Airport, Flight

MIN_LAYOVER_DOMESTIC = timedelta(minutes=45)
MIN_LAYOVER_INTERNATIONAL = timedelta(minutes=90)
MAX_LAYOVER = timedelta(hours=6)
MAX_SEGMENTS = 3  # direct, 1-stop, 2-stop

# The smallest minimum that could ever apply; used to narrow the candidate window
# before the per-connection domestic/international check.
SMALLEST_MIN_LAYOVER = min(MIN_LAYOVER_DOMESTIC, MIN_LAYOVER_INTERNATIONAL)


def is_domestic_connection(
    arriving: Flight, departing: Flight, airports: Mapping[str, Airport]
) -> bool:
    """A connection is domestic only if the whole hop A -> hub -> B stays in one country.

    JFK->ORD->LAX is domestic (all US); JFK->LHR->CDG is international even though
    the connection airport is a single country.
    """
    countries = {
        airports[arriving.origin].country,
        airports[arriving.destination].country,  # the connection airport
        airports[departing.destination].country,
    }
    return len(countries) == 1


def min_layover(arriving: Flight, departing: Flight, airports: Mapping[str, Airport]) -> timedelta:
    if is_domestic_connection(arriving, departing, airports):
        return MIN_LAYOVER_DOMESTIC
    return MIN_LAYOVER_INTERNATIONAL


def is_valid_connection(
    arriving: Flight, departing: Flight, airports: Mapping[str, Airport]
) -> bool:
    """All connection rules for one (arriving, departing) pair. Bounds are inclusive."""
    if arriving.destination != departing.origin:  # no airport change (JFK -> LGA invalid)
        return False
    layover = departing.departure_utc - arriving.arrival_utc
    return min_layover(arriving, departing, airports) <= layover <= MAX_LAYOVER
