import { useState } from 'react';
import AirportInput from './AirportInput.jsx';
import { resolveAirport } from '../utils/airports.js';
import { validateSearch } from '../utils/validation.js';

export const DATASET_DATE = '2024-03-15';

export default function SearchForm({ onSearch, loading, airports, byCode, knownCodes, serverError }) {
  const [values, setValues] = useState({ origin: '', destination: '', date: DATASET_DATE });
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  // Inputs hold what the user typed (a code or a city name). Resolve to codes first,
  // then run the normal code validation; a resolve error (e.g. "New York has 3
  // airports") wins over the generic one for that field.
  const check = (v) => {
    const origin = resolveAirport(v.origin, airports);
    const destination = resolveAirport(v.destination, airports);
    const query = { origin: origin.code ?? '', destination: destination.code ?? '', date: v.date };
    const errs = validateSearch(query, knownCodes);
    if (origin.error) errs.origin = origin.error;
    if (destination.error) errs.destination = destination.error;
    if (origin.error || destination.error) {
      // "Origin and destination must differ" is meaningless if one side didn't resolve.
      if (errs.destination === 'Origin and destination must differ') delete errs.destination;
    }
    return { errs, query };
  };

  const apply = (next) => {
    setValues(next);
    // After the first submit, re-validate live so errors clear as the user fixes them.
    if (submitted) setErrors(check(next).errs);
  };
  const update = (field) => (value) => apply({ ...values, [field]: value });
  const swap = () => apply({ ...values, origin: values.destination, destination: values.origin });

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    const { errs, query } = check(values);
    setErrors(errs);
    if (Object.keys(errs).length === 0) onSearch(query);
  };

  // A 400/422 from the API that names a field is shown next to that field.
  const fieldError = (field) =>
    errors[field] || (serverError?.field === field ? serverError.message : undefined);

  return (
    <form className="search-form" onSubmit={handleSubmit} noValidate aria-label="Flight search">
      <AirportInput
        id="origin"
        label="From"
        value={values.origin}
        onChange={update('origin')}
        error={fieldError('origin')}
        airports={airports}
        byCode={byCode}
      />
      <button
        type="button"
        className="swap"
        onClick={swap}
        aria-label="Swap origin and destination"
        title="Swap"
      >
        ⇄
      </button>
      <AirportInput
        id="destination"
        label="To"
        value={values.destination}
        onChange={update('destination')}
        error={fieldError('destination')}
        airports={airports}
        byCode={byCode}
      />
      <div className={`field ${fieldError('date') ? 'field--error' : ''}`}>
        <label htmlFor="date">Date</label>
        <input
          id="date"
          name="date"
          type="date"
          value={values.date}
          onChange={(e) => update('date')(e.target.value)}
          aria-invalid={Boolean(fieldError('date'))}
          aria-describedby={fieldError('date') ? 'date-error' : undefined}
        />
        {fieldError('date') ? (
          <p id="date-error" className="field__error" role="alert">
            {fieldError('date')}
          </p>
        ) : (
          <p className="field__hint">Schedule covers {DATASET_DATE}</p>
        )}
      </div>
      <button type="submit" className="search-button" disabled={loading}>
        {loading ? 'Searching…' : 'Search flights'}
      </button>
    </form>
  );
}
