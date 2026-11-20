import { DATASET_DATE } from '../SearchForm.jsx';

export default function EmptyState({ query }) {
  const otherDate = query?.date && query.date !== DATASET_DATE;
  return (
    <div className="state state--empty" role="status">
      <div className="state__icon" aria-hidden="true">
        ✈
      </div>
      <h2>No flights found</h2>
      <p>
        There are no direct or connecting flights (up to 2 stops) from{' '}
        <strong>{query?.origin}</strong> to <strong>{query?.destination}</strong> on{' '}
        <strong>{query?.date}</strong>.
      </p>
      {otherDate ? (
        <p className="state__hint">The schedule only covers flights departing on {DATASET_DATE}.</p>
      ) : (
        <p className="state__hint">Try a different airport pair.</p>
      )}
    </div>
  );
}
