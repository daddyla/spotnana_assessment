from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.core.config import get_settings

REAL_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "flights.json"


def airport(code: str, country: str, timezone: str, city: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "name": f"{code} Airport",
        "city": city or code,
        "country": country,
        "timezone": timezone,
    }


def flight(
    number: str, origin: str, destination: str, dep: str, arr: str, price: Any = 100.0
) -> dict[str, Any]:
    return {
        "flightNumber": number,
        "airline": "Test Air",
        "origin": origin,
        "destination": destination,
        "departureTime": dep,
        "arrivalTime": arr,
        "price": price,
        "aircraft": "A320",
    }


# A small cast of airports used across unit tests.
AIRPORTS = [
    airport("JFK", "US", "America/New_York", "New York"),
    airport("LGA", "US", "America/New_York", "New York"),
    airport("EWR", "US", "America/New_York", "New York"),
    airport("ORD", "US", "America/Chicago", "Chicago"),
    airport("LAX", "US", "America/Los_Angeles", "Los Angeles"),
    airport("PHX", "US", "America/Phoenix", "Phoenix"),
    airport("LHR", "GB", "Europe/London", "London"),
    airport("CDG", "FR", "Europe/Paris", "Paris"),
    airport("SYD", "AU", "Australia/Sydney", "Sydney"),
]


@pytest.fixture
def real_data_path() -> Path:
    assert REAL_DATA_PATH.exists(), REAL_DATA_PATH
    return REAL_DATA_PATH


@pytest.fixture
def settings():
    return get_settings()
