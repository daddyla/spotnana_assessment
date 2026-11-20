# SkyPath: Flight Connection Search

Search direct, 1-stop and 2-stop itineraries between two airports over a fixed flight schedule (`data/flights.json`). The backend is FastAPI (Python 3.12) and the frontend is React (Vite, plain JS). Each runs in its own container behind docker-compose.

---

## Running it

```sh
docker-compose up --build
```

| URL | What |
|---|---|
| http://localhost:3000 | Web app |
| http://localhost:8000/docs | Interactive API docs (Swagger) |
| http://localhost:8000/api/data-quality | What the loader cleaned out of the dataset |

If port 8000 or 3000 is already taken: `BACKEND_PORT=8001 FRONTEND_PORT=3001 docker-compose up`.

The dataset is mounted read-only from `./data`. To search a different schedule, replace the file and restart.

### Local development (without Docker)

```sh
# backend: Python 3.11+
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload       # http://localhost:8000
.venv/bin/pytest                              # 75 tests
.venv/bin/python -m scripts.audit_dataset     # print the data-quality report

# frontend: Node 20.19+ or 22.12+ (Vite 7)
cd frontend
npm install
npm run dev                                   # http://localhost:5173 (proxies /api to :8000)
npm test                                      # 20 tests
```

---

## API

`GET /api/search?origin=JFK&destination=LAX&date=2024-03-15`

```jsonc
{
  "origin": { "code": "JFK", "city": "New York", ... },
  "destination": { "code": "LAX", ... },
  "date": "2024-03-15",
  "count": 27,
  "itineraries": [
    {
      "id": "SP101",
      "stops": 0,
      "totalDurationMinutes": 375,
      "totalPrice": 299.0,
      "departureTime": "2024-03-15T08:30:00-04:00",   // local time + UTC offset
      "arrivalTime":   "2024-03-15T11:45:00-07:00",
      "segments": [{ "flightNumber": "SP101", "origin": {...}, "destination": {...},
                     "departureTime": "...", "arrivalTime": "...", "durationMinutes": 375,
                     "price": 299.0, "airline": "...", "aircraft": "A320" }],
      "layovers": [ /* { "airport": {...}, "durationMinutes": 90, "type": "international" } */ ]
    }
  ]
}
```

| Situation | Status | Body |
|---|---|---|
| Results (possibly none) | `200` | as above, `itineraries: []` when nothing matches |
| Malformed input (`JF1`, `2024-02-30`, missing param) | `422` | `{ "detail": "Origin must be a 3-letter airport code (e.g. JFK)", "field": "origin", "errors": [...] }` |
| Unknown airport (`XXX`) | `400` | `{ "detail": "Unknown airport code: XXX", "field": "origin" }` |
| Same origin and destination | `400` | `{ "detail": "Origin and destination must differ", "field": "destination" }` |

Other endpoints: `GET /api/airports`, `GET /api/data-quality`, `GET /health`.

---

## How the search works

1. **At startup**, every local time is converted to UTC using its airport's IANA timezone (`zoneinfo`). Flights are grouped by origin and sorted by UTC departure.
2. **For a query**, every flight that leaves the origin on the requested *local* date starts a depth-first search, up to 3 segments deep.
3. **At each connection airport**, `bisect` jumps to the flights leaving between *arrival + 45 min* and *arrival + 6 h*. Each candidate then has to pass these checks:
   - **Same airport code.** Landing at JFK and leaving from LGA is impossible by construction.
   - **Minimum layover.** 45 min if the arriving flight's origin, the connection airport and the next flight's destination are all in one country; otherwise 90 min.
   - **No revisited airports.** This stops loops like JFK→ORD→JFK→LAX.
4. **Totals** are computed in UTC: duration = last arrival − first departure. Results are sorted by duration, then price, departure time and flight numbers.

A query takes about 0.1 ms on this dataset. A test checks that the search returns exactly the same itineraries as a deliberately naive brute-force version for all 600 airport pairs.

---

## Architecture decisions

| Decision | Why |
|---|---|
| **Monorepo, `backend/` and `frontend/` fully independent** | Each has its own dependencies, Dockerfile and tests. A single git history shows how the whole thing was built. |
| **`domain/` (pure Python) separate from `api/` (FastAPI)** | Search and rules are plain functions over dataclasses, so they're unit-testable without HTTP. The API layer only validates input, maps errors and serialises output. |
| **Clean at load time, keep the raw file untouched** | The provided file has dirty rows: an unknown airport `JKF` and prices stored as strings. Records that can be safely fixed are fixed; records that would need guessing are dropped. Every action is reported (`/api/data-quality`, startup logs). This keeps working if a different file is used. |
| **UTC for arithmetic, local time with offset for display** | This handles the date line (SYD→LAX "arrives before it departs") and DST. On 2024-03-15, PHX→LAX really is 30 min, because Phoenix has no DST and LA switched on March 10. The API returns `2024-03-15T09:00:00+11:00`, and the UI shows the wall-clock part without converting to the browser's timezone. |
| **In-memory store loaded in the FastAPI lifespan** | About 300 static records. A database would add infrastructure with no benefit. Loading at startup means a bad file fails immediately. |
| **Bounded DFS** | The spec asks for *all* itineraries up to 2 stops, not one shortest path. Layover rules depend on pairs of flights (times and countries), which fits a flight-to-flight walk naturally. |
| **Same-origin `/api` (nginx in Docker, Vite proxy in dev)** | No CORS configuration and no backend URL baked into the JS bundle. |
| **Consistent `{detail, field}` errors** | The UI can show the message as-is and attach it to the right input. |

## Tradeoffs considered

- **Search algorithm.**
  - **Dijkstra / A* on a time-expanded graph:** returns a single best path. Listing all paths would need k-shortest-paths, and the pairwise domestic/international rule is awkward to express there.
  - **Connection Scan / RAPTOR:** the right tool for millions of connections, but complex and tuned for earliest arrival.
  - **SQL self-joins:** declarative, but needs a database.
  - **Brute force:** simplest, but O(F³), so it's used only as the test oracle.
  - **Bounded DFS:** gives every result, with the least code, rules checked as it goes, and well under a millisecond here.
- **Dropping vs. fixing `JKF`.** It's almost certainly JFK, but silently changing booking data is worse than leaving one flight out and reporting it.
- **Price as a JSON number.** Sums are exact `Decimal` internally and converted to a number at the API edge for easy display. A real booking API would send integer cents or a string, and a currency (none is in the dataset; USD is assumed).
- **`date` = local departure date at the origin.** This matches how people book. Later segments may depart the next day.
- **No pagination or filters.** At most a few dozen results per query, so the UI shows them all.
- **Inclusive layover bounds.** Exactly 45 min, 90 min or 6 h is valid.

## What I'd improve with more time

- Filters and sorting in the UI (stops, price, departure window, airline) plus pagination for larger datasets.
- Precompute the valid flight-to-flight connection graph at startup and cache results per `(origin, destination, date)`. If the network grew to real-world size, move to CSA/RAPTOR and a real datastore.
- Multi-day schedules: index by date and allow searching a range ("±1 day").
- Treat metro areas such as NYC = JFK/LGA/EWR as a search *input* (search "NYC"), while still forbidding airport changes mid-trip.
- Browser E2E tests (Playwright) running against docker-compose, plus CI (lint, tests, image build).
- Structured logging, request metrics, rate limiting. Return price as integer cents with a currency.
- Accessibility audit and keyboard-navigable airport autocomplete. The native `<datalist>` varies by browser.

## Project layout

```
data/flights.json            raw dataset (unchanged)
backend/app/
  main.py                    app factory, lifespan, error handlers
  api/routes.py              HTTP endpoints
  schemas/search.py          response models + domain→API mapping
  domain/{models,rules,search}.py   pure logic
  data/{loader,store}.py     validation/cleaning + in-memory index
backend/tests/               loader, rules, search (incl. oracle), API
frontend/src/
  api/client.js              fetch wrapper → ApiError
  hooks/                     useAirports, useFlightSearch
  components/                SearchForm, ResultsList, ItineraryCard, ...
  utils/                     validation, timezone-safe formatting
```
