import { useCallback, useEffect, useRef, useState } from 'react';
import { searchFlights } from '../api/client.js';

// status: 'idle' | 'loading' | 'success' | 'error'
export function useFlightSearch() {
  const [state, setState] = useState({ status: 'idle', data: null, error: null, query: null });
  const controllerRef = useRef(null);

  const search = useCallback(async (query) => {
    // A newer search cancels the previous one, so a slow stale response can never
    // overwrite fresher results.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setState((prev) => ({ ...prev, status: 'loading', error: null, query }));
    try {
      const data = await searchFlights(query, { signal: controller.signal });
      setState({ status: 'success', data, error: null, query });
    } catch (err) {
      if (err.name === 'AbortError') return;
      setState({ status: 'error', data: null, error: err, query });
    }
  }, []);

  useEffect(() => () => controllerRef.current?.abort(), []);

  return { ...state, search };
}
