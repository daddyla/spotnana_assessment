import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App.jsx';

const AIRPORTS = [
  { code: 'JFK', name: 'John F. Kennedy International', city: 'New York', country: 'US', timezone: 'America/New_York' },
  { code: 'LAX', name: 'Los Angeles International', city: 'Los Angeles', country: 'US', timezone: 'America/Los_Angeles' },
  { code: 'ORD', name: "O'Hare International", city: 'Chicago', country: 'US', timezone: 'America/Chicago' },
  { code: 'SYD', name: 'Sydney Kingsford Smith', city: 'Sydney', country: 'AU', timezone: 'Australia/Sydney' },
];
const ap = (code) => AIRPORTS.find((a) => a.code === code);

const seg = (flightNumber, o, d, dep, arr, durationMinutes, price) => ({
  flightNumber,
  airline: 'SkyPath Airways',
  aircraft: 'A320',
  origin: ap(o),
  destination: ap(d),
  departureTime: dep,
  arrivalTime: arr,
  durationMinutes,
  price,
});

const SEARCH_JFK_LAX = {
  origin: ap('JFK'),
  destination: ap('LAX'),
  date: '2024-03-15',
  count: 2,
  itineraries: [
    {
      id: 'SP101',
      stops: 0,
      totalDurationMinutes: 375,
      totalPrice: 299,
      departureTime: '2024-03-15T08:30:00-04:00',
      arrivalTime: '2024-03-15T11:45:00-07:00',
      segments: [seg('SP101', 'JFK', 'LAX', '2024-03-15T08:30:00-04:00', '2024-03-15T11:45:00-07:00', 375, 299)],
      layovers: [],
    },
    {
      id: 'SP200-SP210',
      stops: 1,
      totalDurationMinutes: 480,
      totalPrice: 350.5,
      departureTime: '2024-03-15T07:00:00-04:00',
      arrivalTime: '2024-03-15T12:00:00-07:00',
      segments: [
        seg('SP200', 'JFK', 'ORD', '2024-03-15T07:00:00-04:00', '2024-03-15T08:30:00-05:00', 150, 150),
        seg('SP210', 'ORD', 'LAX', '2024-03-15T09:30:00-05:00', '2024-03-15T12:00:00-07:00', 270, 200.5),
      ],
      layovers: [{ airport: ap('ORD'), durationMinutes: 60, type: 'domestic' }],
    },
  ],
};

function jsonResponse(body, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });
}

function mockFetch(searchHandler) {
  globalThis.fetch = vi.fn((url) => {
    if (url.startsWith('/api/airports')) return jsonResponse(AIRPORTS);
    return searchHandler(url);
  });
}

async function fillAndSubmit(user, origin, destination) {
  const from = screen.getByLabelText('From');
  const to = screen.getByLabelText('To');
  await user.clear(from);
  if (origin) await user.type(from, origin);
  await user.clear(to);
  if (destination) await user.type(to, destination);
  await user.click(screen.getByRole('button', { name: /search flights/i }));
}

describe('App', () => {
  let user;
  beforeEach(() => {
    user = userEvent.setup();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows validation errors without calling the API', async () => {
    mockFetch(() => jsonResponse(SEARCH_JFK_LAX));
    render(<App />);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1)); // airports only

    await fillAndSubmit(user, '', '');
    expect(screen.getByText('Origin is required')).toBeInTheDocument();
    expect(screen.getByText('Destination is required')).toBeInTheDocument();

    await fillAndSubmit(user, 'jfk', 'jfk');
    expect(screen.getByText('Origin and destination must differ')).toBeInTheDocument();

    await fillAndSubmit(user, 'XXX', 'LAX');
    expect(screen.getByText('Unknown airport code: XXX')).toBeInTheDocument();

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('shows loading, then results with segments, layovers, duration and price', async () => {
    let resolve;
    mockFetch(() => new Promise((r) => (resolve = r)));
    render(<App />);

    await fillAndSubmit(user, 'JFK', 'LAX');
    expect(screen.getByRole('status')).toHaveTextContent(/searching/i);
    expect(screen.getByRole('button', { name: /searching/i })).toBeDisabled();
    expect(fetch).toHaveBeenLastCalledWith(
      '/api/search?origin=JFK&destination=LAX&date=2024-03-15',
      expect.anything(),
    );

    resolve(await jsonResponse(SEARCH_JFK_LAX));
    expect(await screen.findByText(/2 itineraries/)).toBeInTheDocument();
    expect(screen.getAllByText('6h 15m').length).toBeGreaterThan(0); // summary + segment
    expect(screen.getByText('$299.00')).toBeInTheDocument();
    expect(screen.getByText('Direct')).toBeInTheDocument();

    // Second card is collapsed; expand it to see the layover.
    await user.click(screen.getByRole('button', { name: /8h/ }));
    expect(screen.getByText(/layover in Chicago/)).toBeInTheDocument();
    expect(screen.getByText('domestic')).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    mockFetch(() => jsonResponse({ ...SEARCH_JFK_LAX, count: 0, itineraries: [] }));
    render(<App />);
    await fillAndSubmit(user, 'JFK', 'LAX');
    expect(await screen.findByText('No flights found')).toBeInTheDocument();
  });

  it('shows a field error returned by the API next to the input', async () => {
    mockFetch(() => jsonResponse({ detail: 'Unknown airport code: ORD', field: 'origin' }, 400));
    render(<App />);
    await fillAndSubmit(user, 'ORD', 'LAX');
    expect(await screen.findByText('Unknown airport code: ORD')).toBeInTheDocument();
  });

  it('shows a retryable banner when the service is down', async () => {
    mockFetch(() => Promise.reject(new TypeError('Failed to fetch')));
    render(<App />);
    await fillAndSubmit(user, 'JFK', 'LAX');
    expect(await screen.findByText(/cannot reach the flight search service/i)).toBeInTheDocument();

    fetch.mockImplementation(() => jsonResponse(SEARCH_JFK_LAX));
    await user.click(screen.getByRole('button', { name: /try again/i }));
    expect(await screen.findByText(/2 itineraries/)).toBeInTheDocument();
  });

  it('handles a non-JSON 502 from the proxy', async () => {
    mockFetch(() =>
      Promise.resolve({ ok: false, status: 502, json: () => Promise.reject(new SyntaxError('html')) }),
    );
    render(<App />);
    await fillAndSubmit(user, 'JFK', 'LAX');
    expect(await screen.findByText(/having trouble/i)).toBeInTheDocument();
  });

  it('explains a 404 from the wrong server instead of echoing "Not Found"', async () => {
    mockFetch(() => jsonResponse({ detail: 'Not Found' }, 404));
    render(<App />);
    await fillAndSubmit(user, 'JFK', 'LAX');
    expect(await screen.findByText(/service could not be found/i)).toBeInTheDocument();
    expect(screen.queryByText('Not Found')).not.toBeInTheDocument();
  });

  it('explains date-line arrivals (test case 6)', async () => {
    const dep = '2024-03-15T09:00:00+11:00';
    const arr = '2024-03-15T06:00:00-07:00';
    mockFetch(() =>
      jsonResponse({
        origin: ap('SYD'),
        destination: ap('LAX'),
        date: '2024-03-15',
        count: 1,
        itineraries: [
          {
            id: 'SP540',
            stops: 0,
            totalDurationMinutes: 900,
            totalPrice: 1199,
            departureTime: dep,
            arrivalTime: arr,
            segments: [seg('SP540', 'SYD', 'LAX', dep, arr, 900, 1199)],
            layovers: [],
          },
        ],
      }),
    );
    render(<App />);
    await fillAndSubmit(user, 'SYD', 'LAX');
    expect(await screen.findByText(/arrival looks earlier than departure/i)).toBeInTheDocument();
    expect(screen.getAllByText('15h').length).toBeGreaterThan(0);
  });
});
