import {
  dayDiff,
  formatDayDiff,
  formatDuration,
  formatOffset,
  formatWallDate,
  wallTime,
} from '../utils/format.js';

function Stop({ time, airport, align }) {
  return (
    <div className={`stop stop--${align}`}>
      <div className="stop__time">
        <time dateTime={time}>{wallTime(time)}</time>
      </div>
      <div className="stop__airport">
        <strong>{airport.code}</strong> {airport.city}
      </div>
      <div className="stop__meta">
        {formatWallDate(time)} · {formatOffset(time)}
      </div>
    </div>
  );
}

export default function SegmentRow({ segment }) {
  const shift = dayDiff(segment.departureTime, segment.arrivalTime);
  return (
    <div className="segment">
      <Stop time={segment.departureTime} airport={segment.origin} align="start" />
      <div className="segment__middle">
        <span className="segment__flight">{segment.flightNumber}</span>
        <span className="segment__line" aria-hidden="true" />
        <span className="segment__duration">{formatDuration(segment.durationMinutes)}</span>
        <span className="segment__aircraft">
          {segment.airline} · {segment.aircraft}
        </span>
      </div>
      <Stop time={segment.arrivalTime} airport={segment.destination} align="end" />
      {shift !== 0 && (
        <span className="segment__shift" title="Arrival date differs from departure date">
          {formatDayDiff(shift)}
        </span>
      )}
    </div>
  );
}
