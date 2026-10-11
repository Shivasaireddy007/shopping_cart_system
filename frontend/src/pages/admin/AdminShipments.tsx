import { useState } from 'react'

import { useAdminShipments } from '../../hooks/queries'

const when = new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
const NEEDS_ATTENTION = ['rto initiated', 'undelivered', 'lost', 'damaged']

function ShipmentPill({ status }: { status: string }) {
  const style =
    status === 'delivered' ? 'bg-good-soft text-good'
      : NEEDS_ATTENTION.includes(status) ? 'bg-crit-soft text-crit'
        : status === 'pending' || status === 'created' ? 'bg-warn-soft text-warn'
          : 'bg-good-soft text-good'
  const label = status === 'awb_assigned' ? 'Courier assigned' : status.replace(/\b\w/g, (c) => c.toUpperCase())
  return <span className={`rounded-full px-2 py-1 text-xs font-semibold ${style}`}>{label}</span>
}

export function AdminShipments() {
  const [page, setPage] = useState(1)
  const { data, isPending } = useAdminShipments(page)
  const pages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1

  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-extrabold">Shipments</h1>
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-surface-2 text-left text-xs tracking-wider text-muted uppercase">
            <tr><th className="p-3">AWB</th><th className="p-3">Courier</th><th className="p-3">Order</th><th className="p-3">Status</th><th className="p-3">Updated</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isPending ? (
              <tr><td colSpan={5} className="p-4 text-muted">Loading…</td></tr>
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={5} className="p-4 text-muted">No shipments yet. They're created automatically when orders are paid.</td></tr>
            ) : (
              data?.items.map((s) => (
                <tr key={s.order_number}>
                  <td className="p-3 font-mono text-xs">{s.awb_code ?? '—'}</td>
                  <td className="p-3">{s.courier_name ?? '—'}</td>
                  <td className="p-3 font-mono text-xs">{s.order_number}</td>
                  <td className="p-3"><ShipmentPill status={s.status} /></td>
                  <td className="p-3 text-muted tabular">{s.status_updated_at ? when.format(new Date(s.status_updated_at)) : '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {pages > 1 ? (
        <nav className="flex items-center gap-3 text-sm" aria-label="Pages">
          <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)} className="rounded-lg border border-line bg-surface px-3 py-1.5 disabled:opacity-40">Previous</button>
          <span className="text-muted tabular">Page {page} of {pages}</span>
          <button type="button" disabled={page === pages} onClick={() => setPage(page + 1)} className="rounded-lg border border-line bg-surface px-3 py-1.5 disabled:opacity-40">Next</button>
        </nav>
      ) : null}
    </div>
  )
}
