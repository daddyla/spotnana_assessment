export default function Loading() {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="visually-hidden">Searching for flights…</span>
      {[0, 1, 2].map((i) => (
        <div key={i} className="skeleton" aria-hidden="true" />
      ))}
    </div>
  );
}
