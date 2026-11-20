import { Fragment, useState } from 'react';
import LayoverBadge from './LayoverBadge.jsx';
import SegmentRow from './SegmentRow.jsx';
import {
  arrivesEarlierLocally,
  dayDiff,
  formatDayDiff,
  formatDuration,
  formatPrice,
  formatStops,
  wallTime,
} from '../utils/format.js';

export default function ItineraryCard({ itinerary, rank }) {
  const [open, setOpen] = useState(rank === 0);
  const { segments, layovers, departureTime, arrivalTime } = itinerary;
  const first = segments[0];
  const last = segments[segments.length - 1];
  const shift = dayDiff(departureTime, arrivalTime);
  const via = layovers.map((l) => l.airport.code).join(', ');
  const detailsId = `itinerary-${itinerary.id}`;

  return (
    <article className="card" aria-label={`Itinerary ${itinerary.id}`}>
      <button
        type="button"
        className="card__summary"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={detailsId}
      >
        <div className="summary__times">
          <span className="summary__clock">
            {wallTime(departureTime)} → {wallTime(arrivalTime)}
            {shift !== 0 && <sup className="summary__shift">{formatDayDiff(shift)}</sup>}
          </span>
          <span className="summary__route">
            {first.origin.code} → {last.destination.code}
            {via && <span className="summary__via"> via {via}</span>}
          </span>
        </div>
        <div className="summary__duration">
          <span className="summary__value">{formatDuration(itinerary.totalDurationMinutes)}</span>
          <span className={`summary__stops ${itinerary.stops === 0 ? 'is-direct' : ''}`}>
            {formatStops(itinerary.stops)}
          </span>
        </div>
        <div className="summary__price">
          <span className="summary__value">{formatPrice(itinerary.totalPrice)}</span>
          <span className="summary__flights">{segments.map((s) => s.flightNumber).join(' · ')}</span>
        </div>
        <span className="card__chevron" aria-hidden="true">
          {open ? '▴' : '▾'}
        </span>
      </button>

      {open && (
        <div className="card__details" id={detailsId}>
          {arrivesEarlierLocally(departureTime, arrivalTime) && (
            <p className="note">
              Arrival looks earlier than departure because times are local and this trip flies
              west across time zones (e.g. over the International Date Line). Actual travel time
              is{' '}
              {formatDuration(itinerary.totalDurationMinutes)}.
            </p>
          )}
          {segments.map((segment, i) => (
            <Fragment key={segment.flightNumber}>
              <SegmentRow segment={segment} />
              {layovers[i] && <LayoverBadge layover={layovers[i]} />}
            </Fragment>
          ))}
        </div>
      )}
    </article>
  );
}
