// Airport lookup for the search inputs: suggestion matching and turning what the
// user typed (a code or a city name) into an IATA code.

const CODE_QUERY_RE = /^[A-Za-z]{1,3}$/;

function cityWords(city) {
  return city.toLowerCase().split(/[\s\-.]+/).filter(Boolean);
}

/**
 * How well `airport` matches `query`; lower is better, null = no match.
 *   0  code starts with query        "JF"  -> JFK
 *   1  code contains query (ordered) "FK"  -> JFK,  "H" -> PHX
 *   2  city starts with query        "new" -> New York
 *   3  a later city word starts      "york"-> New York, "kong" -> Hong Kong
 * Codes match only as a contiguous, ordered substring ("JK" does not match JFK).
 * Cities match by word prefix, so "an" does not drag in every city containing "an".
 */
export function matchRank(airport, query) {
  const q = query.trim();
  if (!q) return null;
  if (CODE_QUERY_RE.test(q)) {
    const i = airport.code.indexOf(q.toUpperCase());
    if (i === 0) return 0;
    if (i > 0) return 1;
  }
  const lower = q.toLowerCase();
  const city = airport.city.toLowerCase();
  if (city.startsWith(lower)) return 2;
  if (cityWords(airport.city).some((w) => w.startsWith(lower))) return 3;
  return null;
}

export function matchAirports(airports, query) {
  if (!query.trim()) return airports;
  return airports
    .map((a) => ({ a, rank: matchRank(a, query) }))
    .filter((x) => x.rank !== null)
    .sort((x, y) => x.rank - y.rank || x.a.code.localeCompare(y.a.code))
    .map((x) => x.a);
}

/**
 * Turn the input text into an airport code.
 * Returns { code } or { error } (a message to show under the field).
 * Codes that are well-formed but unknown are passed through as { code } so the
 * normal validation reports "Unknown airport code: XXX".
 */
export function resolveAirport(text, airports) {
  const raw = text.trim();
  if (!raw) return { code: '' };
  if (/^[A-Za-z]{3}$/.test(raw) && airports.some((a) => a.code === raw.toUpperCase())) {
    return { code: raw.toUpperCase() };
  }
  const inCity = airports.filter((a) => a.city.toLowerCase() === raw.toLowerCase());
  if (inCity.length === 1) return { code: inCity[0].code };
  if (inCity.length > 1) {
    const codes = inCity.map((a) => a.code);
    const list = `${codes.slice(0, -1).join(', ')} or ${codes[codes.length - 1]}`;
    return { error: `${inCity[0].city} has ${codes.length} airports. Choose ${list}` };
  }
  if (/^[A-Za-z]{3}$/.test(raw)) return { code: raw.toUpperCase() };
  return { error: `No airport matches “${raw}”. Pick one from the list or enter a 3-letter code` };
}
