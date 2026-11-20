"""In-memory, read-only index over the cleaned dataset."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.data.loader import Dataset, LoadReport, load_dataset
from app.domain.models import Airport, Flight


@dataclass(frozen=True)
class FlightStore:
    airports: dict[str, Airport]
    # departures_by_airport[code] -> flights leaving `code`, sorted by departure_utc
    departures_by_airport: dict[str, list[Flight]]
    # Parallel list of departure instants, so search can `bisect` a time window.
    departure_times_by_airport: dict[str, list[datetime]]
    report: LoadReport

    @classmethod
    def from_dataset(cls, dataset: Dataset) -> FlightStore:
        grouped: dict[str, list[Flight]] = defaultdict(list)
        for flight in dataset.flights:
            grouped[flight.origin].append(flight)
        departures = {
            code: sorted(flights, key=lambda f: (f.departure_utc, f.flight_number))
            for code, flights in grouped.items()
        }
        times = {code: [f.departure_utc for f in flights] for code, flights in departures.items()}
        return cls(
            airports=dataset.airports,
            departures_by_airport=departures,
            departure_times_by_airport=times,
            report=dataset.report,
        )

    @classmethod
    def from_file(cls, path: Path | str) -> FlightStore:
        return cls.from_dataset(load_dataset(path))

    @property
    def flight_count(self) -> int:
        return sum(len(v) for v in self.departures_by_airport.values())
