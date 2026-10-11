type Node = { id: string; x: number; y: number; title: string; sub: string; live: boolean }
type Edge = { from: string; to: string; label?: string }

const W = 150
const H = 58

const NODES: Node[] = [
  { id: 'web', x: 20, y: 60, title: 'Browser', sub: 'React + TypeScript', live: true },
  { id: 'api', x: 225, y: 60, title: 'FastAPI', sub: 'async Python', live: true },
  { id: 'db', x: 430, y: 60, title: 'PostgreSQL', sub: 'orders + outbox', live: true },
  { id: 'relay', x: 635, y: 60, title: 'Outbox relay', sub: 'SKIP LOCKED', live: false },
  { id: 'kafka', x: 840, y: 60, title: 'Kafka', sub: 'orders, products', live: false },
  { id: 'redis', x: 225, y: 200, title: 'Redis', sub: 'cache, view counts', live: true },
  { id: 'pay', x: 20, y: 200, title: 'Razorpay', sub: 'simulated here', live: true },
  { id: 'ship', x: 635, y: 200, title: 'Shipping worker', sub: 'order.paid', live: false },
  { id: 'index', x: 840, y: 200, title: 'Search worker', sub: 'product.changed', live: false },
  { id: 'courier', x: 635, y: 330, title: 'Shiprocket', sub: 'courier + AWB', live: false },
  { id: 'search', x: 840, y: 330, title: 'OpenSearch', sub: 'faceted search', live: false },
]

const EDGES: Edge[] = [
  { from: 'web', to: 'api', label: 'REST + JWT' },
  { from: 'api', to: 'db', label: 'one transaction' },
  { from: 'db', to: 'relay', label: 'unsent events' },
  { from: 'relay', to: 'kafka', label: 'idempotent' },
  { from: 'api', to: 'redis', label: 'read-through' },
  { from: 'api', to: 'pay', label: 'HMAC-signed' },
  { from: 'kafka', to: 'ship' },
  { from: 'kafka', to: 'index' },
  { from: 'ship', to: 'courier' },
  { from: 'index', to: 'search' },
]

const byId = Object.fromEntries(NODES.map((n) => [n.id, n]))

function edgePath(a: Node, b: Node): { d: string; lx: number; ly: number; anchor: 'middle' | 'start' } {
  if (a.y === b.y) {
    const [x1, x2] = b.x > a.x ? [a.x + W, b.x] : [a.x, b.x + W]
    const y = a.y + H / 2
    return { d: `M${x1},${y} L${x2},${y}`, lx: (x1 + x2) / 2, ly: a.y - 10, anchor: 'middle' }
  }
  const x1 = a.x + W / 2
  const x2 = b.x + W / 2
  const y1 = a.y + H
  const y2 = b.y
  return { d: `M${x1},${y1} L${x2},${y2}`, lx: (x1 + x2) / 2 + 8, ly: (y1 + y2) / 2 + 4, anchor: 'start' }
}

/** The system at a glance. Solid boxes run in this demo; dashed ones in the full Docker/Kubernetes stack. */
export function Architecture() {
  return (
    <figure className="grid gap-3">
      <div className="overflow-x-auto">
        <svg viewBox="0 0 1010 410" className="min-w-[46rem]" role="img" aria-labelledby="arch-title arch-desc">
          <title id="arch-title">Architecture</title>
          <desc id="arch-desc">
            The browser calls FastAPI, which writes orders and their events to PostgreSQL in one transaction and caches
            the catalog in Redis. A relay publishes the events to Kafka; workers create shipments with Shiprocket and
            index products into OpenSearch.
          </desc>
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="fill-muted" />
            </marker>
          </defs>
          {EDGES.map((e) => {
            const p = edgePath(byId[e.from], byId[e.to])
            return (
              <g key={`${e.from}-${e.to}`}>
                <path d={p.d} className="stroke-muted" strokeWidth="1.5" fill="none" markerEnd="url(#arrow)" />
                {e.label ? (
                  <text x={p.lx} y={p.ly} textAnchor={p.anchor} className="fill-muted font-mono text-[11px]">{e.label}</text>
                ) : null}
              </g>
            )
          })}
          {NODES.map((n) => (
            <g key={n.id}>
              <rect
                x={n.x}
                y={n.y}
                width={W}
                height={H}
                rx="8"
                className={n.live ? 'fill-surface stroke-brand' : 'fill-surface-2 stroke-muted'}
                strokeWidth={n.live ? 2 : 1.5}
                strokeDasharray={n.live ? undefined : '5 4'}
              />
              <text x={n.x + W / 2} y={n.y + 25} textAnchor="middle" className="fill-ink font-display text-[15px] font-bold">{n.title}</text>
              <text x={n.x + W / 2} y={n.y + 44} textAnchor="middle" className="fill-muted text-[11px]">{n.sub}</text>
            </g>
          ))}
        </svg>
      </div>
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border-2 border-brand bg-surface" /> Running in this demo</span>
        <span className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-dashed border-muted bg-surface-2" /> Full stack (Docker Compose, Kubernetes, CI)</span>
      </figcaption>
    </figure>
  )
}
