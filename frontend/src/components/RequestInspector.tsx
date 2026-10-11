import { useState } from 'react'
import { Link } from 'react-router-dom'

import { type LoggedRequest, useRequestLog } from '../stores/requests'

function CacheBadge({ cache }: { cache: LoggedRequest['cache'] }) {
  if (!cache) return null
  const hit = cache === 'HIT'
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${hit ? 'bg-good-soft text-good' : 'bg-surface-2 text-muted'}`}
      title={hit ? 'Served from the Redis cache' : 'Built from PostgreSQL, then cached in Redis'}
    >
      {hit ? 'REDIS HIT' : 'CACHE MISS'}
    </span>
  )
}

const ms = (value: number) => `${value < 10 ? value.toFixed(1) : Math.round(value)} ms`

/** A small live log of this page's API calls: time in the API, network round trip, and cache use. */
export function RequestInspector() {
  const requests = useRequestLog((s) => s.requests)
  const [open, setOpen] = useState(false)
  const latest = requests[0]

  return (
    <div className="fixed right-4 bottom-[calc(1rem+env(safe-area-inset-bottom,0px))] z-20 flex max-w-[calc(100vw-2rem)] flex-col items-end gap-2">
      {open ? (
        <section
          id="request-inspector"
          aria-label="Live API requests"
          className="w-[26rem] max-w-full overflow-hidden rounded-xl border border-line bg-surface shadow-xl"
        >
          <header className="border-b border-line px-4 py-3">
            <h2 className="font-bold">Live API requests</h2>
            <p className="text-xs text-muted">
              Every call this page makes to the FastAPI backend. "API" is time spent on the server; "total" includes the
              network. <Link to="/how-it-works" className="font-semibold text-brand hover:underline" onClick={() => setOpen(false)}>How it's built</Link>
            </p>
          </header>
          {requests.length ? (
            <ol className="max-h-80 divide-y divide-line overflow-y-auto text-xs">
              {requests.map((r) => (
                <li key={r.id} className="grid gap-1 px-4 py-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-muted">{r.method}</span>
                    <span className="min-w-0 flex-1 truncate font-mono" title={r.path}>{r.path}</span>
                    <span className={`font-mono font-bold ${r.status >= 400 ? 'text-crit' : 'text-good'}`}>{r.status}</span>
                  </div>
                  <div className="flex items-center gap-3 text-muted tabular">
                    {r.serverMs !== null ? <span>API <b className="text-ink">{ms(r.serverMs)}</b></span> : null}
                    <span>total {ms(r.ms)}</span>
                    <CacheBadge cache={r.cache} />
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="px-4 py-6 text-sm text-muted">Browse the shop and its API calls appear here.</p>
          )}
        </section>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="request-inspector"
        className="flex items-center gap-2 rounded-full border border-line bg-ink px-4 py-2 text-xs font-semibold text-white shadow-lg hover:bg-brand"
      >
        <span className="size-2 rounded-full bg-good" aria-hidden="true" />
        {open ? 'Hide requests' : latest?.serverMs != null ? `Last API call ${ms(latest.serverMs)}${latest.cache === 'HIT' ? ' · Redis' : ''}` : 'Live API requests'}
      </button>
    </div>
  )
}
