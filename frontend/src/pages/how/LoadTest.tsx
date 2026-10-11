const ROWS = [
  { label: 'All requests', db: 99.1, cache: 5.5 },
  { label: 'Product listing', db: 95.3, cache: 4.9 },
  { label: 'Product page', db: 90.2, cache: 2.0 },
  { label: 'Search', db: 120.6, cache: 6.2 },
]
const MAX = 125

/** k6 results at 1,000 requests per second: p95 latency with PostgreSQL only vs. with the Redis cache. */
export function LoadTest() {
  return (
    <figure className="grid gap-4">
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-2"><span className="inline-block size-3 rounded-sm bg-muted/40" /> PostgreSQL only</span>
        <span className="flex items-center gap-2"><span className="inline-block size-3 rounded-sm bg-brand" /> With Redis cache</span>
      </div>
      <dl className="grid gap-4">
        {ROWS.map((row) => (
          <div key={row.label} className="grid gap-1.5 sm:grid-cols-[9rem_1fr] sm:items-center sm:gap-4">
            <dt className="text-sm font-semibold">{row.label}</dt>
            <dd className="grid gap-1">
              {[
                { value: row.db, className: 'bg-muted/40', name: 'PostgreSQL only' },
                { value: row.cache, className: 'bg-brand', name: 'With Redis cache' },
              ].map((bar) => (
                <div key={bar.name} className="flex items-center gap-2" title={`${bar.name}: p95 ${bar.value} ms`}>
                  <span className={`h-3 rounded-r ${bar.className}`} style={{ width: `${(bar.value / MAX) * 100}%`, minWidth: '3px' }} />
                  <span className="shrink-0 text-xs tabular">{bar.value} ms</span>
                </div>
              ))}
            </dd>
          </div>
        ))}
      </dl>
      <figcaption className="text-xs text-muted">
        p95 latency at a steady 1,000 requests per second on a 100,000-product catalog, measured with k6. Without the
        cache, 63 requests couldn't be served in time; with it, none were dropped.
      </figcaption>
    </figure>
  )
}
