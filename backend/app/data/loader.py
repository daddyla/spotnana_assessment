"""Parse, validate and clean the raw flights dataset.

Policy:
- The raw JSON file is never modified; cleaning happens here, at load time.
- A record that can be safely normalised (e.g. price "95.00" -> Decimal) is
  *coerced* and kept.
- An unknown airport code that is exactly one swapped pair of letters away from
  exactly one known code (e.g. origin "JKF" -> "JFK") is *corrected* as a typo and
  reported. Anything less certain (no match, several matches) is *dropped*.
- Every coercion / drop is recorded in a LoadReport so it is visible, not silent.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.models import Airport, Flight

logger = logging.getLogger(__name__)

AIRPORT_CODE_RE = re.compile(r"^[A-Z]{3}$")
MAX_FLIGHT_DURATION = timedelta(hours=24)

REQUIRED_AIRPORT_FIELDS = ("code", "name", "city", "country", "timezone")
REQUIRED_FLIGHT_FIELDS = (
    "flightNumber",
    "origin",
    "destination",
    "departureTime",
    "arrivalTime",
    "price",
)


class RecordError(ValueError):
    """Raised while parsing a single record; the record is dropped."""


@dataclass(frozen=True)
class Issue:
    action: Literal["dropped", "coerced"]
    entity: Literal["airport", "flight"]
    id: str
    reason: str


@dataclass
class LoadReport:
    airports_total: int = 0
    airports_loaded: int = 0
    flights_total: int = 0
    flights_loaded: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def dropped(self) -> list[Issue]:
        return [i for i in self.issues if i.action == "dropped"]

    @property
    def coerced(self) -> list[Issue]:
        return [i for i in self.issues if i.action == "coerced"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "airportsTotal": self.airports_total,
            "airportsLoaded": self.airports_loaded,
            "flightsTotal": self.flights_total,
            "flightsLoaded": self.flights_loaded,
            "dropped": [asdict(i) for i in self.dropped],
            "coerced": [asdict(i) for i in self.coerced],
        }

    def summary(self) -> str:
        return (
            f"airports {self.airports_loaded}/{self.airports_total} loaded, "
            f"flights {self.flights_loaded}/{self.flights_total} loaded, "
            f"{len(self.dropped)} dropped, {len(self.coerced)} coerced"
        )


@dataclass(frozen=True)
class Dataset:
    airports: dict[str, Airport]
    flights: list[Flight]
    report: LoadReport


# --------------------------------------------------------------------------- helpers


def localize(naive: datetime, tz: ZoneInfo) -> datetime:
    """Attach a timezone to a naive local time, rejecting times that don't exist.

    During a DST "spring forward" gap (e.g. 02:30 on 2024-03-10 in New York) a
    local wall-clock time never happens. zoneinfo would silently shift it, so we
    round-trip through UTC to detect that and refuse the record instead.
    """
    aware = naive.replace(tzinfo=tz)
    roundtrip = aware.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    if roundtrip != naive:
        raise RecordError(f"local time {naive.isoformat()} does not exist in {tz.key} (DST gap)")
    return aware


def _parse_naive_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise RecordError(f"{field_name} is not a string: {value!r}")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RecordError(f"{field_name} is not ISO 8601: {value!r}") from exc
    if dt.tzinfo is not None:
        # Spec says times are local airport time; an explicit offset would conflict.
        raise RecordError(f"{field_name} has an unexpected UTC offset: {value!r}")
    return dt


def _parse_price(value: Any) -> tuple[Decimal, bool]:
    """Return (price, was_coerced). Accepts numbers and numeric strings."""
    coerced = False
    if isinstance(value, bool):  # bool is a subclass of int — reject explicitly
        raise RecordError(f"price is a boolean: {value!r}")
    if isinstance(value, str):
        coerced = True
        raw = value.strip()
    elif isinstance(value, int | float):
        raw = str(value)  # str() avoids binary-float artefacts in Decimal(0.1)
    else:
        raise RecordError(f"price has unsupported type: {value!r}")
    try:
        price = Decimal(raw)
    except InvalidOperation as exc:
        raise RecordError(f"price is not numeric: {value!r}") from exc
    if not price.is_finite() or price <= 0:
        raise RecordError(f"price must be a positive number: {value!r}")
    return price.quantize(Decimal("0.01")), coerced


def _normalize_code(value: Any, field_name: str) -> tuple[str, bool]:
    if not isinstance(value, str):
        raise RecordError(f"{field_name} is not a string: {value!r}")
    code = value.strip().upper()
    if not AIRPORT_CODE_RE.match(code):
        raise RecordError(f"{field_name} is not a 3-letter IATA code: {value!r}")
    return code, code != value


def _correct_typo(code: str, airports: dict[str, Airport]) -> str | None:
    """Known code reachable by swapping two adjacent letters, if exactly one exists.

    Only adjacent transpositions ("JKF" -> "JFK") are tried: it is the most common
    keying slip and, with 3-letter codes, rarely ambiguous. If two known codes fit,
    we refuse to guess and the record is dropped.
    """
    swaps = {code[:i] + code[i + 1] + code[i] + code[i + 2 :] for i in range(len(code) - 1)}
    matches = sorted(c for c in swaps if c in airports and c != code)
    return matches[0] if len(matches) == 1 else None


def _require(record: dict[str, Any], fields: tuple[str, ...]) -> None:
    missing = [f for f in fields if record.get(f) in (None, "")]
    if missing:
        raise RecordError(f"missing required field(s): {', '.join(missing)}")


# --------------------------------------------------------------------------- parsing


def _parse_airport(raw: dict[str, Any], report: LoadReport) -> Airport:
    _require(raw, REQUIRED_AIRPORT_FIELDS)
    code, code_changed = _normalize_code(raw["code"], "code")
    if code_changed:
        report.issues.append(
            Issue("coerced", "airport", code, f"code normalised from {raw['code']!r}")
        )
    try:
        tz = ZoneInfo(raw["timezone"])
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RecordError(f"unknown timezone: {raw['timezone']!r}") from exc
    return Airport(
        code=code,
        name=str(raw["name"]),
        city=str(raw["city"]),
        country=str(raw["country"]).strip().upper(),
        timezone=raw["timezone"],
        tz=tz,
    )


def _resolve_code(
    code: str, label: str, number: str, airports: dict[str, Airport], report: LoadReport
) -> str:
    if code in airports:
        return code
    fixed = _correct_typo(code, airports)
    if fixed is None:
        raise RecordError(f"{label} {code!r} is not a known airport")
    report.issues.append(
        Issue("coerced", "flight", number, f"typo: {label} {code!r} corrected to {fixed!r}")
    )
    return fixed


def _parse_flight(raw: dict[str, Any], airports: dict[str, Airport], report: LoadReport) -> Flight:
    _require(raw, REQUIRED_FLIGHT_FIELDS)
    number = str(raw["flightNumber"]).strip()

    origin, _ = _normalize_code(raw["origin"], "origin")
    destination, _ = _normalize_code(raw["destination"], "destination")
    origin = _resolve_code(origin, "origin", number, airports, report)
    destination = _resolve_code(destination, "destination", number, airports, report)
    if origin == destination:
        raise RecordError(f"origin and destination are both {origin}")

    dep_local = localize(
        _parse_naive_datetime(raw["departureTime"], "departureTime"), airports[origin].tz
    )
    arr_local = localize(
        _parse_naive_datetime(raw["arrivalTime"], "arrivalTime"), airports[destination].tz
    )
    dep_utc = dep_local.astimezone(UTC)
    arr_utc = arr_local.astimezone(UTC)
    duration = arr_utc - dep_utc
    if duration <= timedelta(0):
        raise RecordError(f"arrives before it departs (UTC duration {duration})")
    if duration > MAX_FLIGHT_DURATION:
        raise RecordError(f"implausible duration {duration}")

    price, price_coerced = _parse_price(raw["price"])
    if price_coerced:
        report.issues.append(
            Issue("coerced", "flight", number, f"price string {raw['price']!r} -> {price}")
        )

    return Flight(
        flight_number=number,
        airline=str(raw.get("airline") or ""),
        origin=origin,
        destination=destination,
        departure_local=dep_local,
        arrival_local=arr_local,
        departure_utc=dep_utc,
        arrival_utc=arr_utc,
        price=price,
        aircraft=str(raw.get("aircraft") or ""),
    )


def parse_dataset(raw: dict[str, Any]) -> Dataset:
    """Validate and normalise an already-decoded dataset dict."""
    report = LoadReport()
    raw_airports = raw.get("airports") or []
    raw_flights = raw.get("flights") or []
    report.airports_total = len(raw_airports)
    report.flights_total = len(raw_flights)

    airports: dict[str, Airport] = {}
    for index, item in enumerate(raw_airports):
        ident = str(item.get("code", f"#{index}")) if isinstance(item, dict) else f"#{index}"
        try:
            if not isinstance(item, dict):
                raise RecordError("airport record is not an object")
            airport = _parse_airport(item, report)
            if airport.code in airports:
                raise RecordError("duplicate airport code")
            airports[airport.code] = airport
        except RecordError as exc:
            report.issues.append(Issue("dropped", "airport", ident, str(exc)))

    flights: list[Flight] = []
    seen_numbers: set[str] = set()
    for index, item in enumerate(raw_flights):
        ident = (
            str(item.get("flightNumber", f"#{index}")) if isinstance(item, dict) else f"#{index}"
        )
        # Collect coercions separately so a dropped record doesn't leave
        # misleading "coerced" entries behind.
        local_report = LoadReport()
        try:
            if not isinstance(item, dict):
                raise RecordError("flight record is not an object")
            flight = _parse_flight(item, airports, local_report)
            if flight.flight_number in seen_numbers:
                # The dataset is one day; a repeated number means a duplicate row.
                raise RecordError("duplicate flight number")
            seen_numbers.add(flight.flight_number)
            flights.append(flight)
            report.issues.extend(local_report.issues)
        except RecordError as exc:
            report.issues.append(Issue("dropped", "flight", ident, str(exc)))

    report.airports_loaded = len(airports)
    report.flights_loaded = len(flights)
    return Dataset(airports=airports, flights=flights, report=report)


def load_dataset(path: Path | str) -> Dataset:
    """Read the JSON file and return a cleaned Dataset. Logs the load report."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: top-level JSON must be an object")
    dataset = parse_dataset(raw)
    logger.info("Loaded dataset %s: %s", path, dataset.report.summary())
    for issue in dataset.report.issues:
        logger.warning("%s %s %s: %s", issue.action, issue.entity, issue.id, issue.reason)
    return dataset
