import ResultsList from './components/ResultsList.jsx';
import SearchForm from './components/SearchForm.jsx';
import EmptyState from './components/states/EmptyState.jsx';
import ErrorBanner from './components/states/ErrorBanner.jsx';
import Loading from './components/states/Loading.jsx';
import { useAirports } from './hooks/useAirports.js';
import { useFlightSearch } from './hooks/useFlightSearch.js';

function Results({ status, data, error, query, onRetry }) {
  if (status === 'loading') return <Loading />;
  if (status === 'error') {
    // Errors tied to a form field are rendered inline by the form instead.
    return error.field ? null : <ErrorBanner error={error} onRetry={onRetry} />;
  }
  if (status === 'success') {
    return data.itineraries.length === 0 ? <EmptyState query={query} /> : <ResultsList data={data} />;
  }
  return (
    <p className="state state--idle">
      Enter two airports to search direct, 1-stop and 2-stop itineraries.
    </p>
  );
}

export default function App() {
  const { airports, byCode, knownCodes } = useAirports();
  const { status, data, error, query, search } = useFlightSearch();

  return (
    <div className="app">
      <header className="app__header">
        <h1>
          <span aria-hidden="true">✈</span> SkyPath
        </h1>
        <p>Find direct and connecting flights</p>
      </header>
      <main>
        <SearchForm
          onSearch={search}
          loading={status === 'loading'}
          airports={airports}
          byCode={byCode}
          knownCodes={knownCodes}
          serverError={
            status === 'error' && error?.field ? { field: error.field, message: error.message } : null
          }
        />
        <Results
          status={status}
          data={data}
          error={error}
          query={query}
          onRetry={() => query && search(query)}
        />
      </main>
    </div>
  );
}
