import ItineraryCard from './ItineraryCard.jsx';
import { formatWallDate } from '../utils/format.js';

export default function ResultsList({ data }) {
  const { origin, destination, itineraries, count } = data;
  const dateLabel = formatWallDate(`${data.date}T00:00:00`);
  return (
    <section className="results" aria-labelledby="results-heading">
      <div className="results__header">
        <h2 id="results-heading">
          {origin.city} ({origin.code}) → {destination.city} ({destination.code})
        </h2>
        <p>
          {count} itinerar{count === 1 ? 'y' : 'ies'} on {dateLabel} · sorted by shortest travel
          time · times shown in local airport time
        </p>
      </div>
      <ol className="results__list">
        {itineraries.map((it, i) => (
          <li key={it.id}>
            <ItineraryCard itinerary={it} rank={i} />
          </li>
        ))}
      </ol>
    </section>
  );
}
