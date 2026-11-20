export default function AirportInput({ id, label, value, onChange, error, airports, byCode }) {
  const listId = `${id}-options`;
  const errorId = `${id}-error`;
  const match = byCode.get(value);

  return (
    <div className={`field ${error ? 'field--error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={id}
        list={listId}
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3))}
        placeholder="e.g. JFK"
        autoComplete="off"
        spellCheck="false"
        maxLength={3}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      />
      <datalist id={listId}>
        {airports.map((a) => (
          <option key={a.code} value={a.code}>
            {a.city} — {a.name}
          </option>
        ))}
      </datalist>
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
