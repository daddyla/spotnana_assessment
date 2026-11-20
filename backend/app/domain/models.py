"""Core domain objects. Plain dataclasses — no FastAPI / Pydantic here."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    city: str
    country: str
    timezone: str
    tz: ZoneInfo = field(compare=False, repr=False)


@dataclass(frozen=True)
class Flight:
    flight_number: str
    airline: str
    origin: str
    destination: str
    # Timezone-aware datetimes in the *airport's local* zone (keeps the UTC offset,
    # which is what the UI needs to display "06:00 PDT").
    departure_local: datetime
    arrival_local: datetime
    # Same instants normalised to UTC: every comparison / duration uses these.
    departure_utc: datetime
    arrival_utc: datetime
    price: Decimal
    aircraft: str

    @property
    def duration(self) -> timedelta:
        return self.arrival_utc - self.departure_utc
