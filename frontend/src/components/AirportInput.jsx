import { useId, useMemo, useState } from 'react';

/**
 * Airport code input with a custom suggestion list (ARIA combobox pattern).
 *
 * Matching is on the IATA code only, as a contiguous, ordered substring:
 *   "H"  -> HKG, HND, LHR, PHX
 *   "JF" -> JFK          ("FJ" matches nothing: order matters)
 * The native <datalist> was dropped because each browser matches differently
 * (Chrome also matches city/name text), so "H" showed unrelated airports.
 */
export function matchAirports(airports, query) {
  const q = query.trim().toUpperCase();
  if (!q) return airports;
  return airports
    .filter((a) => a.code.includes(q))
    .sort((a, b) => a.code.indexOf(q) - b.code.indexOf(q) || a.code.localeCompare(b.code));
}

function Highlight({ code, query }) {
  const i = query ? code.indexOf(query) : -1;
  if (i < 0) return code;
  return (
    <>
      {code.slice(0, i)}
      <mark>{code.slice(i, i + query.length)}</mark>
      {code.slice(i + query.length)}
    </>
  );
}

export default function AirportInput({ id, label, value, onChange, error, airports, byCode }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = `${id}-listbox`;
  const errorId = `${id}-error`;
  const optionId = useId();
  const match = byCode.get(value);

  const suggestions = useMemo(() => matchAirports(airports, value), [airports, value]);
  // Hide the list once the user has typed an exact code; there is nothing left to choose.
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
            onChange(e.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3));
            setActive(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. JFK"
          autoComplete="off"
          spellCheck="false"
          maxLength={3}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
        {showList && (
          <ul className="combo__list" id={listId} role="listbox" aria-label={`${label} airports`}>
            {suggestions.length === 0 ? (
              <li className="combo__empty">No airport code contains “{value}”</li>
            ) : (
              suggestions.map((a, i) => (
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
                    <Highlight code={a.code} query={value} />
                  </span>
                  <span className="combo__place">
                    {a.city}, {a.country}
                    <small>{a.name}</small>
                  </span>
                </li>
              ))
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
