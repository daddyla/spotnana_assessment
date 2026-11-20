import { useState } from 'react';
import AirportInput from './AirportInput.jsx';
import { validateSearch } from '../utils/validation.js';

export const DATASET_DATE = '2024-03-15';

export default function SearchForm({ onSearch, loading, airports, byCode, knownCodes, serverError }) {
  const [values, setValues] = useState({ origin: '', destination: '', date: DATASET_DATE });
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const apply = (next) => {
    setValues(next);
    // After the first submit, re-validate live so errors clear as the user fixes them.
    if (submitted) setErrors(validateSearch(next, knownCodes));
  };
  const update = (field) => (value) => apply({ ...values, [field]: value });
  const swap = () => apply({ ...values, origin: values.destination, destination: values.origin });

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    const found = validateSearch(values, knownCodes);
    setErrors(found);
    if (Object.keys(found).length === 0) onSearch(values);
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
