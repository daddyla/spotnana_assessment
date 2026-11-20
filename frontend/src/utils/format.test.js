import { describe, expect, it } from 'vitest';
import {
  arrivesEarlierLocally,
  dayDiff,
  formatDayDiff,
  formatDuration,
  formatOffset,
  formatStops,
  formatWallDate,
  wallTime,
} from './format.js';

describe('format helpers', () => {
  it('formats durations', () => {
    expect(formatDuration(30)).toBe('30m');
    expect(formatDuration(375)).toBe('6h 15m');
    expect(formatDuration(900)).toBe('15h');
  });

  it('reads wall-clock time from the string, ignoring the browser timezone', () => {
    expect(wallTime('2024-03-15T09:00:00+11:00')).toBe('09:00');
    expect(formatWallDate('2024-03-15T23:30:00-07:00')).toBe('Fri, Mar 15');
  });

  it('formats UTC offsets', () => {
    expect(formatOffset('2024-03-15T09:00:00+11:00')).toBe('UTC+11');
    expect(formatOffset('2024-03-15T09:00:00-04:00')).toBe('UTC−4');
    expect(formatOffset('2024-03-15T09:00:00+05:30')).toBe('UTC+5:30');
    expect(formatOffset('2024-03-15T09:00:00+00:00')).toBe('UTC');
  });

  it('computes day shifts between local dates', () => {
    expect(dayDiff('2024-03-15T22:00:00-07:00', '2024-03-17T02:00:00+09:00')).toBe(2);
    expect(formatDayDiff(1)).toBe('+1 day');
    expect(formatDayDiff(2)).toBe('+2 days');
    expect(formatDayDiff(-1)).toBe('−1 day');
    expect(formatDayDiff(0)).toBe('');
  });

  it('detects date-line style "arrives before it departs" (test case 6)', () => {
    expect(arrivesEarlierLocally('2024-03-15T09:00:00+11:00', '2024-03-15T06:00:00-07:00')).toBe(
      true,
    );
    expect(arrivesEarlierLocally('2024-03-15T08:30:00-04:00', '2024-03-15T11:45:00-07:00')).toBe(
      false,
    );
  });

  it('labels stops', () => {
    expect(formatStops(0)).toBe('Direct');
    expect(formatStops(1)).toBe('1 stop');
    expect(formatStops(2)).toBe('2 stops');
  });
});
