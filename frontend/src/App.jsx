import SearchForm from './components/SearchForm.jsx';
import { useAirports } from './hooks/useAirports.js';
import { useFlightSearch } from './hooks/useFlightSearch.js';

export default function App() {
  const { airports, byCode, knownCodes } = useAirports();
  const { status, data, error, search } = useFlightSearch();

  return (
    <div className="app">
      <header className="app__header">
        <h1>SkyPath</h1>
        <p>Find direct and connecting flights</p>
      </header>
      <main>
        <SearchForm
          onSearch={search}
          loading={status === 'loading'}
          airports={airports}
          byCode={byCode}
          knownCodes={knownCodes}
          serverError={error?.field ? { field: error.field, message: error.message } : null}
        />
        {status === 'success' && <p>{data.count} itineraries found</p>}
        {status === 'error' && <p role="alert">{error.message}</p>}
      </main>
    </div>
  );
}
