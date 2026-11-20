export default function ErrorBanner({ error, onRetry }) {
  // Field-level errors (400/422 naming a field) are already shown next to the input;
  // this banner covers everything else, and offers retry for transient failures.
  const retryable = !error.status || error.status >= 500;
  return (
    <div className="state state--error" role="alert">
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      {retryable && onRetry && (
        <button type="button" className="retry" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
