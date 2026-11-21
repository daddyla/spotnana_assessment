from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import REAL_DATA_PATH


@pytest.fixture(scope="module")
def client():
    app = create_app(Settings(data_path=REAL_DATA_PATH))
    with TestClient(app) as c:  # `with` runs the lifespan (dataset load)
        yield c


def _search(client, origin, destination, date="2024-03-15"):
    return client.get(
        "/api/search", params={"origin": origin, "destination": destination, "date": date}
    )


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "airports": 25, "flights": 303}


def test_airports_listed_sorted(client):
    codes = [a["code"] for a in client.get("/api/airports").json()]
    assert len(codes) == 25 and codes == sorted(codes)


def test_data_quality_report(client):
    body = client.get("/api/data-quality").json()
    assert body["dropped"] == []
    assert sorted(c["id"] for c in body["coerced"]) == ["SP995", "SP995", "SP996", "SP998"]
    assert any(c["reason"].startswith("typo:") for c in body["coerced"])


# ------------------------------------------------------------------ spec test cases


def test_case_1_jfk_lax_shape_and_ordering(client):
    res = _search(client, "JFK", "LAX")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == len(body["itineraries"]) > 3
    assert {it["stops"] for it in body["itineraries"]} == {0, 1, 2}
    durations = [it["totalDurationMinutes"] for it in body["itineraries"]]
    assert durations == sorted(durations)

    first = body["itineraries"][0]
    assert first["stops"] == 0 and first["totalDurationMinutes"] == 375
    seg = first["segments"][0]
    assert seg["flightNumber"] in {"SP101", "SP102", "SP103"}
    assert seg["origin"]["code"] == "JFK" and seg["destination"]["code"] == "LAX"
    assert seg["departureTime"].endswith("-04:00")  # local time keeps its offset (EDT)
    assert seg["arrivalTime"].endswith("-07:00")  # PDT


def test_connection_payload_has_layovers(client):
    body = _search(client, "BOS", "SEA").json()
    it = body["itineraries"][0]
    assert it["id"] == "SP260-SP221"
    assert len(it["layovers"]) == it["stops"] == 1
    lay = it["layovers"][0]
    assert lay["airport"]["code"] == "DEN"
    assert lay["type"] == "domestic" and lay["durationMinutes"] >= 45
    assert it["totalPrice"] == pytest.approx(sum(s["price"] for s in it["segments"]))


def test_case_2_sfo_nrt_international_layovers(client):
    body = _search(client, "SFO", "NRT").json()
    intl = [
        lay for it in body["itineraries"] for lay in it["layovers"] if lay["type"] != "domestic"
    ]
    assert intl and all(lay["durationMinutes"] >= 90 for lay in intl)


def test_case_4_same_airport(client):
    res = _search(client, "JFK", "JFK")
    assert res.status_code == 400
    assert res.json() == {"detail": "Origin and destination must differ", "field": "destination"}


@pytest.mark.parametrize(
    ("origin", "destination", "field"), [("XXX", "LAX", "origin"), ("JFK", "QQQ", "destination")]
)
def test_case_5_unknown_airport(client, origin, destination, field):
    res = _search(client, origin, destination)
    assert res.status_code == 400
    body = res.json()
    assert body["field"] == field
    assert "Unknown airport code" in body["detail"]


def test_case_6_syd_lax_date_line(client):
    body = _search(client, "SYD", "LAX").json()
    sp540 = next(it for it in body["itineraries"] if it["id"] == "SP540")
    seg = sp540["segments"][0]
    assert seg["departureTime"] == "2024-03-15T09:00:00+11:00"
    assert seg["arrivalTime"] == "2024-03-15T06:00:00-07:00"
    assert sp540["totalDurationMinutes"] == 15 * 60


# ------------------------------------------------------------------ input validation


def test_lowercase_codes_accepted(client):
    assert _search(client, "jfk", "lax").json()["origin"]["code"] == "JFK"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"origin": "JF", "destination": "LAX", "date": "2024-03-15"}, "origin"),
        ({"origin": "JF1", "destination": "LAX", "date": "2024-03-15"}, "origin"),
        ({"origin": "JFK", "destination": "LAXX", "date": "2024-03-15"}, "destination"),
        ({"origin": "JFK", "destination": "LAX", "date": "15-03-2024"}, "date"),
        ({"origin": "JFK", "destination": "LAX", "date": "2024-02-30"}, "date"),
        ({"origin": "JFK", "destination": "LAX"}, "date"),
    ],
)
def test_malformed_input_is_422_with_friendly_message(client, params, field):
    res = client.get("/api/search", params=params)
    assert res.status_code == 422
    body = res.json()
    assert body["field"] == field
    assert isinstance(body["detail"], str) and body["detail"]


def test_date_without_flights_returns_empty_list(client):
    res = _search(client, "JFK", "LAX", "2025-01-01")
    assert res.status_code == 200
    assert res.json()["itineraries"] == [] and res.json()["count"] == 0
