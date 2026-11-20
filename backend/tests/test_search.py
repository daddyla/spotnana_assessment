from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from itertools import permutations

import pytest

from app.data.loader import parse_dataset
from app.data.store import FlightStore
from app.domain.rules import MAX_SEGMENTS, is_valid_connection
from app.domain.search import (
    SameAirportError,
    UnknownAirportError,
    search_itineraries,
)
from tests.conftest import AIRPORTS, flight

D = date(2024, 3, 15)


def _store(*raw) -> FlightStore:
    ds = parse_dataset({"airports": AIRPORTS, "flights": list(raw)})
    assert len(ds.flights) == len(raw), ds.report.issues
    return FlightStore.from_dataset(ds)


def _numbers(itineraries):
    return [tuple(f.flight_number for f in it.segments) for it in itineraries]


@pytest.fixture(scope="module")
def real_store(request) -> FlightStore:
    from tests.conftest import REAL_DATA_PATH

    return FlightStore.from_file(REAL_DATA_PATH)


# ------------------------------------------------------------------ unit (fixtures)


def test_direct_one_stop_and_two_stop_are_all_found():
    store = _store(
        flight("D1", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00"),
        flight("A1", "JFK", "ORD", "2024-03-15T07:00:00", "2024-03-15T08:30:00"),
        flight("A2", "ORD", "LAX", "2024-03-15T10:00:00", "2024-03-15T12:30:00"),
        flight("B1", "ORD", "PHX", "2024-03-15T09:30:00", "2024-03-15T11:30:00"),
        flight("B2", "PHX", "LAX", "2024-03-15T13:00:00", "2024-03-15T13:30:00"),
    )
    result = _numbers(search_itineraries(store, "JFK", "LAX", D))
    assert set(result) == {("D1",), ("A1", "A2"), ("A1", "B1", "B2")}


def test_results_sorted_by_total_duration_then_price():
    store = _store(
        flight("SLOW", "JFK", "LAX", "2024-03-15T06:00:00", "2024-03-15T10:00:00", 50),
        flight("FAST_PRICY", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00", 300),
        flight("FAST_CHEAP", "JFK", "LAX", "2024-03-15T09:00:00", "2024-03-15T12:00:00", 200),
    )
    result = search_itineraries(store, "JFK", "LAX", D)
    assert _numbers(result) == [("FAST_CHEAP",), ("FAST_PRICY",), ("SLOW",)]
    assert result[0].total_duration == timedelta(hours=6)


def test_three_stops_are_never_returned():
    store = _store(
        flight("1", "JFK", "ORD", "2024-03-15T06:00:00", "2024-03-15T07:00:00"),
        flight("2", "ORD", "PHX", "2024-03-15T08:00:00", "2024-03-15T10:00:00"),
        flight("3", "PHX", "EWR", "2024-03-15T11:00:00", "2024-03-15T17:00:00"),
        flight("4", "EWR", "LAX", "2024-03-15T18:00:00", "2024-03-15T21:00:00"),
    )
    assert search_itineraries(store, "JFK", "LAX", D) == []


def test_loops_through_origin_are_excluded():
    store = _store(
        flight("1", "JFK", "ORD", "2024-03-15T06:00:00", "2024-03-15T07:00:00"),
        flight("2", "ORD", "JFK", "2024-03-15T08:00:00", "2024-03-15T11:00:00"),
        flight("3", "JFK", "LAX", "2024-03-15T12:00:00", "2024-03-15T15:00:00"),
    )
    # Only the direct remains; JFK->ORD->JFK->LAX is rejected.
    assert _numbers(search_itineraries(store, "JFK", "LAX", D)) == [("3",)]


def test_airport_change_is_not_a_connection():
    store = _store(
        flight("1", "ORD", "EWR", "2024-03-15T06:00:00", "2024-03-15T09:00:00"),
        flight("2", "JFK", "LAX", "2024-03-15T11:00:00", "2024-03-15T14:00:00"),
    )
    assert search_itineraries(store, "ORD", "LAX", D) == []


def test_date_is_local_departure_date_at_origin():
    # 23:30 on the 15th in New York is already the 16th in UTC.
    store = _store(
        flight("LATE", "JFK", "LAX", "2024-03-15T23:30:00", "2024-03-16T02:30:00"),
        flight("NEXT", "JFK", "LAX", "2024-03-16T08:00:00", "2024-03-16T11:00:00"),
    )
    assert _numbers(search_itineraries(store, "JFK", "LAX", D)) == [("LATE",)]


def test_connection_may_continue_on_the_next_day():
    store = _store(
        flight("1", "LAX", "JFK", "2024-03-15T22:00:00", "2024-03-16T06:30:00"),
        flight("2", "JFK", "LHR", "2024-03-16T08:00:00", "2024-03-16T20:00:00"),
    )
    result = search_itineraries(store, "LAX", "LHR", D)
    assert _numbers(result) == [("1", "2")]
    assert result[0].layovers[0].duration == timedelta(minutes=90)
    assert result[0].layovers[0].domestic is False


def test_itinerary_totals():
    store = _store(
        flight("1", "JFK", "ORD", "2024-03-15T07:00:00", "2024-03-15T08:30:00", "99.10"),
        flight("2", "ORD", "LAX", "2024-03-15T10:00:00", "2024-03-15T12:30:00", 100.25),
    )
    (it,) = search_itineraries(store, "JFK", "LAX", D)
    assert str(it.total_price) == "199.35"
    assert it.total_duration == timedelta(hours=8, minutes=30)  # 11:00Z -> 19:30Z
    assert it.stops == 1
    assert it.layovers[0].airport == "ORD"
    assert it.layovers[0].duration == timedelta(minutes=90)


def test_unknown_airport_and_same_airport_raise():
    store = _store()
    with pytest.raises(UnknownAirportError, match="XXX"):
        search_itineraries(store, "XXX", "LAX", D)
    with pytest.raises(SameAirportError):
        search_itineraries(store, "JFK", "JFK", D)


# ------------------------------------------------------------------ spec test cases (real data)


def test_case_1_jfk_lax_has_direct_and_multi_stop(real_store):
    result = search_itineraries(real_store, "JFK", "LAX", D)
    stops = Counter(it.stops for it in result)
    assert stops[0] == 3 and stops[1] > 0 and stops[2] > 0
    # Directs are the fastest and come first.
    assert {it.segments[0].flight_number for it in result[:3]} == {"SP101", "SP102", "SP103"}


def test_case_2_sfo_nrt_international_layovers_at_least_90(real_store):
    result = search_itineraries(real_store, "SFO", "NRT", D)
    layovers = [lay for it in result for lay in it.layovers]
    international = [lay for lay in layovers if not lay.domestic]
    assert international, "expected connections onto/off the international leg"
    assert all(lay.duration >= timedelta(minutes=90) for lay in international)
    # A 2-stop like SFO->SEA->LAX->NRT has a *domestic* first layover (SFO, SEA, LAX
    # all US): only 45 min applies there. Every layover still respects its own rule.
    assert all(lay.duration >= timedelta(minutes=45) for lay in layovers)


def test_case_3_bos_sea_only_connections(real_store):
    result = search_itineraries(real_store, "BOS", "SEA", D)
    assert result
    assert all(it.stops >= 1 for it in result)
    best = result[0]
    assert [f.flight_number for f in best.segments] == ["SP260", "SP221"]
    assert best.total_duration == timedelta(hours=10, minutes=30)


def test_case_4_same_airport_is_rejected(real_store):
    with pytest.raises(SameAirportError):
        search_itineraries(real_store, "JFK", "JFK", D)


def test_case_5_unknown_airport_is_rejected(real_store):
    with pytest.raises(UnknownAirportError):
        search_itineraries(real_store, "XXX", "LAX", D)


def test_case_6_syd_lax_date_line(real_store):
    result = search_itineraries(real_store, "SYD", "LAX", D)
    direct = next(it for it in result if it.segments[0].flight_number == "SP540")
    seg = direct.segments[0]
    assert seg.arrival_local.replace(tzinfo=None) < seg.departure_local.replace(tzinfo=None)
    assert direct.total_duration == timedelta(hours=15)


def test_phx_lax_is_thirty_minutes(real_store):
    result = search_itineraries(real_store, "PHX", "LAX", D)
    assert result[0].total_duration == timedelta(minutes=30)


def test_dropped_flight_never_appears(real_store):
    for it in search_itineraries(real_store, "JFK", "LAX", D):
        assert all(f.flight_number != "SP995" for f in it.segments)


# ------------------------------------------------------------------ oracle cross-check


def _oracle(store: FlightStore, origin: str, destination: str, travel_date: date):
    """Deliberately naive: scan every flight at every step, no bisect, no pruning."""
    flights = [f for fs in store.departures_by_airport.values() for f in fs]
    found = set()

    def extend(path):
        last = path[-1]
        if last.destination == destination:
            found.add(tuple(f.flight_number for f in path))
            return
        if len(path) == MAX_SEGMENTS:
            return
        visited = {origin} | {f.destination for f in path}
        for nxt in flights:
            if nxt.destination not in visited and is_valid_connection(last, nxt, store.airports):
                extend([*path, nxt])

    for f in flights:
        if f.origin == origin and f.departure_local.date() == travel_date:
            extend([f])
    return found


def test_search_matches_naive_oracle_for_every_airport_pair(real_store):
    for origin, destination in permutations(sorted(real_store.airports), 2):
        fast = set(_numbers(search_itineraries(real_store, origin, destination, D)))
        assert fast == _oracle(real_store, origin, destination, D), (origin, destination)
