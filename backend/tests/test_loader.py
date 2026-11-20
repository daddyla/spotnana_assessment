from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from app.data.loader import load_dataset, parse_dataset
from tests.conftest import AIRPORTS, airport, flight


def _parse(flights, airports=None):
    return parse_dataset({"airports": airports or AIRPORTS, "flights": flights})


def _dropped_ids(ds):
    return {i.id for i in ds.report.dropped}


# ------------------------------------------------------------------ time zones


def test_local_times_are_converted_to_utc():
    ds = _parse([flight("T1", "JFK", "LAX", "2024-03-15T08:30:00", "2024-03-15T11:45:00")])
    f = ds.flights[0]
    # New York is EDT (UTC-4) and LA is PDT (UTC-7) on 2024-03-15.
    assert f.departure_utc.isoformat() == "2024-03-15T12:30:00+00:00"
    assert f.arrival_utc.isoformat() == "2024-03-15T18:45:00+00:00"
    assert f.duration == timedelta(hours=6, minutes=15)


def test_date_line_crossing_has_positive_duration():
    # SYD -> LAX arrives "earlier" in local time than it departs.
    ds = _parse([flight("T1", "SYD", "LAX", "2024-03-15T09:00:00", "2024-03-15T06:00:00")])
    assert ds.flights[0].duration == timedelta(hours=15)


def test_phoenix_no_dst_uses_iana_rules():
    # Phoenix stays UTC-7; LA moved to UTC-7 on 2024-03-10 -> same clock on 03-15.
    ds = _parse([flight("T1", "PHX", "LAX", "2024-03-15T06:00:00", "2024-03-15T06:30:00")])
    assert ds.flights[0].duration == timedelta(minutes=30)


def test_nonexistent_local_time_in_dst_gap_is_dropped():
    # 02:30 on 2024-03-10 never happened in New York (clocks jumped 02:00 -> 03:00).
    ds = _parse([flight("T1", "JFK", "ORD", "2024-03-10T02:30:00", "2024-03-10T05:00:00")])
    assert ds.flights == []
    assert "DST gap" in ds.report.dropped[0].reason


# ------------------------------------------------------------------ cleaning rules


@pytest.mark.parametrize(
    ("raw_price", "expected"),
    [("289.00", Decimal("289.00")), ("99", Decimal("99.00")), (" 95.5 ", Decimal("95.50"))],
)
def test_numeric_string_price_is_coerced(raw_price, expected):
    ds = _parse(
        [flight("T1", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00", raw_price)]
    )
    assert ds.flights[0].price == expected
    assert [i.id for i in ds.report.coerced] == ["T1"]


def test_numeric_price_is_not_reported_as_coerced():
    ds = _parse([flight("T1", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00", 109)])
    assert ds.flights[0].price == Decimal("109.00")
    assert ds.report.issues == []


@pytest.mark.parametrize("bad_price", ["abc", "", None, -5, 0, True, "NaN", [1]])
def test_invalid_price_is_dropped(bad_price):
    ds = _parse(
        [flight("T1", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00", bad_price)]
    )
    assert ds.flights == []
    assert _dropped_ids(ds) == {"T1"}


def test_unknown_airport_is_dropped_not_guessed():
    ds = _parse([flight("T1", "JKF", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00")])
    assert ds.flights == []
    assert "not a known airport" in ds.report.dropped[0].reason


def test_dropped_flight_does_not_leave_coercion_entries():
    # Bad origin AND string price: only the drop should be reported.
    ds = _parse([flight("T1", "JKF", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00", "289")])
    assert ds.report.coerced == []
    assert len(ds.report.dropped) == 1


@pytest.mark.parametrize(
    ("dep", "arr", "reason"),
    [
        ("2024-03-15T10:00:00", "2024-03-15T07:00:00", "arrives before"),  # JFK->ORD negative
        ("2024-03-15T10:00:00", "2024-03-17T10:00:00", "implausible"),
        ("not-a-date", "2024-03-15T10:00:00", "ISO 8601"),
        ("2024-03-15T10:00:00+00:00", "2024-03-15T12:00:00", "offset"),
    ],
)
def test_invalid_times_are_dropped(dep, arr, reason):
    ds = _parse([flight("T1", "JFK", "ORD", dep, arr)])
    assert ds.flights == []
    assert reason in ds.report.dropped[0].reason


def test_same_origin_and_destination_is_dropped():
    ds = _parse([flight("T1", "JFK", "JFK", "2024-03-15T08:00:00", "2024-03-15T11:00:00")])
    assert ds.flights == []


def test_missing_required_field_is_dropped():
    raw = flight("T1", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00")
    del raw["arrivalTime"]
    ds = _parse([raw])
    assert "arrivalTime" in ds.report.dropped[0].reason


def test_duplicate_flight_number_keeps_first():
    ds = _parse(
        [
            flight("T1", "JFK", "LAX", "2024-03-15T08:00:00", "2024-03-15T11:00:00"),
            flight("T1", "JFK", "ORD", "2024-03-15T09:00:00", "2024-03-15T10:30:00"),
        ]
    )
    assert [f.destination for f in ds.flights] == ["LAX"]
    assert ds.report.dropped[0].reason == "duplicate flight number"


def test_lowercase_codes_are_normalised():
    ds = _parse([flight("T1", "jfk", "lax", "2024-03-15T08:00:00", "2024-03-15T11:00:00")])
    assert (ds.flights[0].origin, ds.flights[0].destination) == ("JFK", "LAX")


def test_invalid_airports_are_dropped():
    airports = [
        *AIRPORTS,
        airport("BAD", "XX", "Not/AZone"),
        airport("JFK", "US", "America/New_York"),  # duplicate
        airport("TOOLONG", "US", "America/New_York"),
    ]
    ds = _parse([], airports)
    assert len(ds.airports) == len(AIRPORTS)
    assert {i.id for i in ds.report.dropped} == {"BAD", "JFK", "TOOLONG"}


# ------------------------------------------------------------------ the real file


def test_real_dataset_cleaning_report(real_data_path):
    ds = load_dataset(real_data_path)
    report = ds.report
    assert (report.airports_total, report.airports_loaded) == (25, 25)
    assert (report.flights_total, report.flights_loaded) == (303, 302)
    assert {(i.id, i.action) for i in report.issues} == {
        ("SP995", "dropped"),  # origin "JKF"
        ("SP996", "coerced"),  # price "99"
        ("SP998", "coerced"),  # price "95.00"
    }
