import { useId, useMemo, useState } from 'react';
import { matchAirports, matchRank } from '../utils/airports.js';

/**
 * Airport input with a custom suggestion list (ARIA combobox pattern).
 * Accepts an IATA code or a city name; see utils/airports.js for the matching rules.
 * The native <datalist> was dropped because each browser matches differently.
 */

function Highlight({ text, query, upper }) {
  const q = upper ? query.toUpperCase() : query.toLowerCase();
  const hay = upper ? text : text.toLowerCase();
  // For cities, highlight the word-prefix that matched ("york" in "New York").
  let i = hay.indexOf(q);
  if (!upper && i > 0 && /[a-z]/.test(hay[i - 1])) i = hay.indexOf(` ${q}`) + 1 || -1;
  if (!q || i < 0) return text;
  return (
    <>
      {text.slice(0, i)}
      <mark>{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </>
  );
}

export default function AirportInput({ id, label, value, onChange, error, airports, byCode }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = `${id}-listbox`;
  const errorId = `${id}-error`;
  const optionId = useId();
  const query = value.trim();
  const match = byCode.get(query.toUpperCase());

  const suggestions = useMemo(() => matchAirports(airports, value), [airports, value]);
  // Hide the list once an exact code is typed; there is nothing left to choose.
  const showList = open && airports.length > 0 && !(match && suggestions.length === 1);

  const select = (airport) => {
    onChange(airport.code);
    setOpen(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && showList && suggestions[active]) {
      e.preventDefault(); // pick the suggestion instead of submitting the form
      select(suggestions[active]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className={`field ${error ? 'field--error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      <div className="combo">
        <input
          id={id}
          name={id}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && suggestions[active] ? `${optionId}-${active}` : undefined}
          value={value}
          onChange={(e) => {
            // Letters, spaces, dots and hyphens only (enough for "St. Louis", "Rio de Janeiro").
            onChange(e.target.value.replace(/[^A-Za-z\s.-]/g, '').slice(0, 40));
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          placeholder="Code or city, e.g. JFK"
          autoComplete="off"
          spellCheck="false"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
        {showList && (
          <ul className="combo__list" id={listId} role="listbox" aria-label={`${label} airports`}>
            {suggestions.length === 0 ? (
              <li className="combo__empty">No airport code or city matches “{query}”</li>
            ) : (
              suggestions.map((a, i) => {
                const rank = query ? matchRank(a, query) : null;
                return (
                  <li
                    key={a.code}
                    id={`${optionId}-${i}`}
                    role="option"
                    aria-selected={i === active}
                    className={`combo__option ${i === active ? 'is-active' : ''}`}
                    // mousedown (not click) so it fires before the input's blur closes the list
                    onMouseDown={(e) => {
                      e.preventDefault();
                      select(a);
                    }}
                    onMouseEnter={() => setActive(i)}
                  >
                    <span className="combo__code">
                      {rank !== null && rank <= 1 ? <Highlight text={a.code} query={query} upper /> : a.code}
                    </span>
                    <span className="combo__place">
                      <span>
                        {rank >= 2 ? <Highlight text={a.city} query={query} /> : a.city}, {a.country}
                      </span>
                      <small>{a.name}</small>
                    </span>
                  </li>
                );
              })
            )}
          </ul>
        )}
      </div>
      {error ? (
        <p id={errorId} className="field__error" role="alert">
          {error}
        </p>
      ) : (
        <p className="field__hint">{match ? `${match.city}, ${match.country}` : ' '}</p>
      )}
    </div>
  );
}
