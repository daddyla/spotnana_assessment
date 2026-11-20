import { describe, expect, it } from 'vitest';
import { validateSearch } from './validation.js';

const known = new Set(['JFK', 'LAX', 'SYD']);
const ok = { origin: 'JFK', destination: 'LAX', date: '2024-03-15' };

describe('validateSearch', () => {
  it('accepts a valid search', () => {
    expect(validateSearch(ok, known)).toEqual({});
  });

  it('requires all fields', () => {
    expect(validateSearch({ origin: '', destination: '', date: '' }, known)).toEqual({
      origin: 'Origin is required',
      destination: 'Destination is required',
      date: 'Date is required',
    });
  });

  it('rejects malformed codes', () => {
    expect(validateSearch({ ...ok, origin: 'JF' }, known).origin).toMatch(/3-letter/);
  });

  it('rejects unknown codes when the airport list is loaded (test case 5)', () => {
    expect(validateSearch({ ...ok, origin: 'XXX' }, known).origin).toBe('Unknown airport code: XXX');
  });

  it('skips the unknown-code check when the airport list failed to load', () => {
    expect(validateSearch({ ...ok, origin: 'XXX' }, null)).toEqual({});
  });

  it('rejects identical origin and destination (test case 4)', () => {
    expect(validateSearch({ ...ok, destination: 'JFK' }, known).destination).toBe(
      'Origin and destination must differ',
    );
  });

  it('rejects impossible dates', () => {
    expect(validateSearch({ ...ok, date: '2024-02-30' }, known).date).toMatch(/valid date/);
    expect(validateSearch({ ...ok, date: '15/03/2024' }, known).date).toMatch(/valid date/);
  });
});
