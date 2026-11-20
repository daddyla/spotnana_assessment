import { useEffect, useMemo, useState } from 'react';
import { getAirports } from '../api/client.js';

// Loads the airport list once for autocomplete + client validation.
// If it fails, the form still works: the backend remains the source of truth.
export function useAirports() {
  const [airports, setAirports] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getAirports({ signal: controller.signal })
      .then((list) => {
        setAirports(list);
        setLoaded(true);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setLoaded(false);
      });
    return () => controller.abort();
  }, []);

  const byCode = useMemo(() => new Map(airports.map((a) => [a.code, a])), [airports]);
  const knownCodes = useMemo(() => (loaded ? new Set(byCode.keys()) : null), [loaded, byCode]);

  return { airports, byCode, knownCodes };
}
