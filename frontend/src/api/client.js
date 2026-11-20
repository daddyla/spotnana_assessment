// Thin fetch wrapper. Every failure becomes an ApiError with a message that is
// safe to show to the user, plus the offending `field` when the backend says so.

export class ApiError extends Error {
  constructor(message, { status = 0, field = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.field = field;
  }
}

async function request(path, { signal } = {}) {
  let response;
  try {
    response = await fetch(path, { signal, headers: { Accept: 'application/json' } });
  } catch (err) {
    if (err.name === 'AbortError') throw err; // caller cancelled; not a user-facing error
    throw new ApiError('Cannot reach the flight search service. Please try again.');
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON body (e.g. proxy 502 HTML page) — handled below.
  }

  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : null;
    // Our API never returns 404 for a valid route, so a 404 means the request reached
    // the wrong server (e.g. a misconfigured proxy). Don't echo its "Not Found".
    if (response.status === 404) {
      throw new ApiError(
        'The flight search service could not be found. Check that the backend is running and the API address is configured correctly.',
        { status: 404 },
      );
    }
    const fallback =
      response.status >= 500
        ? 'The flight search service is having trouble. Please try again shortly.'
        : `Request failed (${response.status}).`;
    throw new ApiError(detail || fallback, { status: response.status, field: body?.field ?? null });
  }
  if (body === null) {
    throw new ApiError('Received an invalid response from the server.', { status: response.status });
  }
  return body;
}

export function searchFlights({ origin, destination, date }, options) {
  const params = new URLSearchParams({ origin, destination, date });
  return request(`/api/search?${params}`, options);
}

export function getAirports(options) {
  return request('/api/airports', options);
}
