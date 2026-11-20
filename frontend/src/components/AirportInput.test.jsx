import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import AirportInput from './AirportInput.jsx';
import { matchAirports } from '../utils/airports.js';

const CODES = ['JFK', 'LGA', 'EWR', 'LAX', 'PHX', 'LHR', 'HND', 'HKG', 'NRT', 'SYD'];
const AIRPORTS = CODES.map((code) => ({ code, name: `${code} Intl`, city: `${code} City`, country: 'XX', timezone: 'UTC' }));
const codesOf = (list) => list.map((a) => a.code);

describe('matchAirports', () => {
  it('matches codes containing the letter anywhere', () => {
    expect(codesOf(matchAirports(AIRPORTS, 'H')).sort()).toEqual(['HKG', 'HND', 'LHR', 'PHX']);
  });

  it('requires the letters in order and next to each other', () => {
    expect(codesOf(matchAirports(AIRPORTS, 'JF'))).toEqual(['JFK']);
    expect(matchAirports(AIRPORTS, 'FJ')).toEqual([]);
    expect(matchAirports(AIRPORTS, 'JK')).toEqual([]); // J and K are not adjacent in JFK
  });

  it('ranks codes that start with the query first', () => {
    expect(codesOf(matchAirports(AIRPORTS, 'H'))).toEqual(['HKG', 'HND', 'LHR', 'PHX']);
    expect(codesOf(matchAirports(AIRPORTS, 'R'))).toEqual(['EWR', 'LHR', 'NRT']); // none start with R, so A–Z
  });

  it('ignores case and does not match the airport name', () => {
    expect(codesOf(matchAirports(AIRPORTS, 'jf'))).toEqual(['JFK']);
    expect(matchAirports(AIRPORTS, 'NTL')).toEqual([]); // letters from "Intl" in every name
  });

  it('returns everything for an empty query', () => {
    expect(matchAirports(AIRPORTS, '')).toHaveLength(AIRPORTS.length);
  });
});

function Harness() {
  const [value, setValue] = useState('');
  const byCode = new Map(AIRPORTS.map((a) => [a.code, a]));
  return <AirportInput id="origin" label="From" value={value} onChange={setValue} airports={AIRPORTS} byCode={byCode} />;
}

describe('AirportInput', () => {
  it('shows only codes containing what was typed, in order', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByRole('combobox', { name: 'From' });

    await user.type(input, 'h');
    const options = within(screen.getByRole('listbox')).getAllByRole('option');
    expect(options.map((o) => o.textContent.slice(0, 3))).toEqual(['HKG', 'HND', 'LHR', 'PHX']);

    await user.clear(input);
    await user.type(input, 'JF');
    expect(within(screen.getByRole('listbox')).getAllByRole('option')).toHaveLength(1);
  });

  it('says so when nothing matches', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.type(screen.getByRole('combobox'), 'FJ');
    expect(screen.getByText(/No airport code or city matches/)).toBeInTheDocument();
  });

  it('selects with the keyboard and closes the list', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByRole('combobox');
    await user.type(input, 'H');
    await user.keyboard('{ArrowDown}{Enter}'); // HKG -> HND
    expect(input).toHaveValue('HND');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('selects with the mouse', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByRole('combobox');
    await user.type(input, 'X');
    await user.click(screen.getByRole('option', { name: /PHX/ }));
    expect(input).toHaveValue('PHX');
  });

  it('closes on Escape', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.type(screen.getByRole('combobox'), 'L');
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });
});
