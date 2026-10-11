import { Link } from 'react-router-dom'

import { RevenueChart } from '../../components/RevenueChart'
import { useDashboard } from '../../hooks/queries'
import { formatPaise } from '../../lib/money'

function Tile({ label, value, note, tone }: { label: string; value: string; note?: string; tone?: 'warn' | 'crit' }) {
  const noteColor = tone === 'crit' ? 'text-crit' : tone === 'warn' ? 'text-warn' : 'text-muted'
  return (
    <div className="grid content-start gap-1 rounded-xl border border-line bg-surface p-4">
      <span className="text-sm font-semibold text-muted">{label}</span>
      <span className="text-2xl font-bold tabular">{value}</span>
      {note ? <span className={`text-xs font-semibold ${noteColor}`}>{note}</span> : null}
    </div>
  )
}

export function AdminDashboard() {
  const { data, isPending, isError } = useDashboard()

  if (isError) return <p className="rounded-lg bg-crit-soft p-4 text-crit">Couldn't load the dashboard.</p>
  if (isPending) return <p className="text-muted">Loading…</p>

  const week = data.revenue_by_day.reduce((sum, d) => sum + d.revenue, 0)

  return (
    <div className="grid gap-5">
      <h1 className="text-2xl font-extrabold">Today</h1>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label="Orders" value={String(data.orders_today)} />
        <Tile label="Revenue" value={formatPaise(data.revenue_today)} note={`${formatPaise(week)} in 7 days`} />
        <Tile label="To ship" value={String(data.to_ship)} note={data.to_ship ? 'Paid, waiting for a courier' : 'All caught up'} tone={data.to_ship ? 'warn' : undefined} />
        <Tile label="Failed payments" value={String(data.failed_payments_today)} tone={data.failed_payments_today ? 'crit' : undefined} note={data.failed_payments_today ? 'Customers may retry' : undefined} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <section className="grid content-start gap-4 rounded-xl border border-line bg-surface p-4" aria-labelledby="revenue-title">
          <h2 id="revenue-title" className="font-bold">Revenue <span className="font-normal text-muted">· last 7 days</span></h2>
          <RevenueChart days={data.revenue_by_day} />
        </section>
        <div className="grid content-start gap-4">
          <section className="grid gap-2 rounded-xl border border-line bg-surface p-4" aria-labelledby="stock-title">
            <h2 id="stock-title" className="font-bold">Low stock <span className="font-normal text-muted">· under 5</span></h2>
            {data.low_stock.length ? (
              <ul className="grid gap-2 text-sm">
                {data.low_stock.map((p) => (
                  <li key={p.id} className="flex items-center justify-between gap-3">
                    <Link to="/admin/products" className="min-w-0 truncate hover:text-brand">{p.name}</Link>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${p.stock === 0 ? 'bg-crit-soft text-crit' : 'bg-warn-soft text-warn'}`}>
                      {p.stock === 0 ? 'Sold out' : `${p.stock} left`}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">Everything is well stocked.</p>
            )}
          </section>
          <section className="grid gap-2 rounded-xl border border-line bg-surface p-4" aria-labelledby="hot-title">
            <h2 id="hot-title" className="font-bold">Most viewed <span className="font-normal text-muted">· 24 hours</span></h2>
            {data.hot_products.length ? (
              <ol className="grid gap-2 text-sm">
                {data.hot_products.map((p) => (
                  <li key={p.id} className="flex justify-between gap-3">
                    <span className="min-w-0 truncate">{p.name}</span>
                    <span className="text-muted tabular">{p.views.toLocaleString('en-IN')} views</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-muted">No product views yet today.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
