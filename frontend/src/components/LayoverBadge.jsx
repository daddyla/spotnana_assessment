import { formatDuration } from '../utils/format.js';

export default function LayoverBadge({ layover }) {
  const { airport, durationMinutes, type } = layover;
  const min = type === 'domestic' ? 45 : 90;
  return (
    <div className="layover" aria-label={`Layover in ${airport.city}`}>
      <span className="layover__icon" aria-hidden="true">
        ⏱
      </span>
      <span>
        <strong>{formatDuration(durationMinutes)}</strong> layover in {airport.city} ({airport.code})
      </span>
      <span
        className={`tag tag--${type}`}
        title={`${type === 'domestic' ? 'Domestic' : 'International'} connection — minimum ${min} min`}
      >
        {type}
      </span>
    </div>
  );
}
