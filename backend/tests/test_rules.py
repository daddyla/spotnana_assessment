from __future__ import annotations

import pytest

from app.data.loader import parse_dataset
from app.domain.rules import is_domestic_connection, is_valid_connection
from tests.conftest import AIRPORTS, flight


def _flights(*raw):
    ds = parse_dataset({"airports": AIRPORTS, "flights": list(raw)})
    assert len(ds.flights) == len(raw), ds.report.issues
    return ds.airports, ds.flights


def _pair(a_route, b_route, b_dep):
    """Arriving flight lands at 12:00 local (New York / London) on 2024-03-15."""
    a_org, a_dst = a_route
    b_org, b_dst = b_route
    # Departure chosen so the first leg has a positive duration (JFK->LHR is overnight).
    a_dep = "2024-03-15T00:00:00" if a_dst == "LHR" else "2024-03-15T09:00:00"
    return _flights(
        flight("A", a_org, a_dst, a_dep, "2024-03-15T12:00:00"),
        flight("B", b_org, b_dst, f"2024-03-15T{b_dep}:00", "2024-03-15T23:00:00"),
    )


def test_domestic_when_all_three_airports_share_a_country():
    airports, (a, b) = _pair(("ORD", "JFK"), ("JFK", "LAX"), "13:00")
    assert is_domestic_connection(a, b, airports)


def test_international_when_any_leg_leaves_the_country():
    # Spec example: JFK -> LHR -> CDG is international.
    airports, (a, b) = _pair(("JFK", "LHR"), ("LHR", "CDG"), "14:00")
    assert not is_domestic_connection(a, b, airports)


@pytest.mark.parametrize(
    ("b_dep", "valid"),
    [
        ("12:44", False),  # 44 min
        ("12:45", True),  # exactly 45 min: inclusive
        ("18:00", True),  # exactly 6 h: inclusive
        ("18:01", False),  # 6 h 1 min
    ],
)
def test_domestic_layover_bounds(b_dep, valid):
    airports, (a, b) = _pair(("ORD", "JFK"), ("JFK", "LAX"), b_dep)
    assert is_valid_connection(a, b, airports) is valid


@pytest.mark.parametrize(
    ("b_dep", "valid"),
    [("13:00", False), ("13:29", False), ("13:30", True)],  # 60, 89, 90 min
)
def test_international_layover_needs_90_minutes(b_dep, valid):
    airports, (a, b) = _pair(("JFK", "LHR"), ("LHR", "CDG"), b_dep)
    assert is_valid_connection(a, b, airports) is valid


def test_same_layover_is_valid_domestic_but_not_international():
    # 60 minutes at JFK: fine onward to LAX, too short onward to LHR.
    airports, (a, b_dom) = _pair(("ORD", "JFK"), ("JFK", "LAX"), "13:00")
    _, (_, b_int) = _pair(("ORD", "JFK"), ("JFK", "LHR"), "13:00")
    assert is_valid_connection(a, b_dom, airports)
    assert not is_valid_connection(a, b_int, airports)


def test_cannot_change_airports_during_layover():
    # Land at EWR, depart JFK two hours later: same city, still invalid.
    airports, (a, b) = _pair(("ORD", "EWR"), ("JFK", "LAX"), "14:00")
    assert not is_valid_connection(a, b, airports)
