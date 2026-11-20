// Formatting helpers. The API returns local airport times as ISO strings WITH an
// offset ("2024-03-15T09:00:00+11:00"). We deliberately read the wall-clock parts
// straight from the string instead of `new Date(iso)`, which would convert to the
// *browser's* timezone and show a Sydney departure in, say, London time.

export function formatDuration(totalMinutes) {
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h === 0) return `${m}m`;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

/** "2024-03-15T09:05:00+11:00" -> "09:05" */
export function wallTime(iso) {
  return iso.slice(11, 16);
}

/** "2024-03-15T..." -> "2024-03-15" */
export function wallDate(iso) {
  return iso.slice(0, 10);
}

function toUtcDate(ymd) {
  const [y, m, d] = ymd.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

/** "2024-03-15T..." -> "Fri, Mar 15" (computed in UTC so it never shifts a day) */
export function formatWallDate(iso) {
  return toUtcDate(wallDate(iso)).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

/** "...+05:30" -> "UTC+5:30", "...-04:00" -> "UTC−4", "...Z" -> "UTC" */
export function formatOffset(iso) {
  const raw = iso.slice(19);
  if (!raw || raw === 'Z' || raw === '+00:00') return 'UTC';
  const sign = raw[0] === '-' ? '−' : '+';
  const [hh, mm] = raw.slice(1).split(':');
  return `UTC${sign}${Number(hh)}${mm && mm !== '00' ? `:${mm}` : ''}`;
}

/** Calendar-day difference between two local dates (e.g. arrival vs departure). */
export function dayDiff(fromIso, toIso) {
  return Math.round((toUtcDate(wallDate(toIso)) - toUtcDate(wallDate(fromIso))) / 86_400_000);
}

export function formatDayDiff(n) {
  if (n === 0) return '';
  return `${n > 0 ? '+' : '−'}${Math.abs(n)} day${Math.abs(n) > 1 ? 's' : ''}`;
}

/** True when the local arrival clock reads earlier than the local departure clock. */
export function arrivesEarlierLocally(depIso, arrIso) {
  return arrIso.slice(0, 16) < depIso.slice(0, 16);
}

// The dataset has no currency field; SkyPath prices are assumed to be USD.
const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
export function formatPrice(value) {
  return money.format(value);
}

export function formatStops(stops) {
  if (stops === 0) return 'Direct';
  return `${stops} stop${stops > 1 ? 's' : ''}`;
}
