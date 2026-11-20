// Client-side validation mirrors the backend rules so users get instant feedback.
// The backend still validates everything — this is UX, not security.

const IATA_RE = /^[A-Z]{3}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function isRealDate(value) {
  if (!DATE_RE.test(value)) return false;
  const [y, m, d] = value.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

/**
 * @param {{origin: string, destination: string, date: string}} values (codes upper-cased)
 * @param {Set<string> | null} knownCodes airport codes from /api/airports; null if not loaded
 * @returns {Record<string, string>} field -> message; empty object when valid
 */
export function validateSearch({ origin, destination, date }, knownCodes) {
  const errors = {};

  for (const [field, value, label] of [
    ['origin', origin, 'Origin'],
    ['destination', destination, 'Destination'],
  ]) {
    if (!value) errors[field] = `${label} is required`;
    else if (!IATA_RE.test(value)) errors[field] = `${label} must be a 3-letter airport code`;
    else if (knownCodes && !knownCodes.has(value)) errors[field] = `Unknown airport code: ${value}`;
  }

  if (!errors.origin && !errors.destination && origin === destination) {
    errors.destination = 'Origin and destination must differ';
  }

  if (!date) errors.date = 'Date is required';
  else if (!isRealDate(date)) errors.date = 'Enter a valid date (YYYY-MM-DD)';

  return errors;
}
