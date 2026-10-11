import { useState } from 'react'

import { OrderStatus } from '../../components/OrderStatus'
import { useAdminOrders } from '../../hooks/queries'
import { formatPaise } from '../../lib/money'

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'pending_payment', label: 'Awaiting payment' },
  { value: 'paid', label: 'Paid' },
  { value: 'shipped', label: 'Shipped' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'cancelled', label: 'Cancelled' },
]
const when = new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' })

function PaymentPill({ status, method }: { status: string | null | undefined; method: string | null | undefined }) {
  if (!status) return <span className="text-muted">—</span>
  const style = status === 'captured' ? 'bg-good-soft text-good' : 'bg-crit-soft text-crit'
  return <span className={`rounded-full px-2 py-1 text-xs font-semibold ${style}`}>{status === 'captured' ? 'Paid' : 'Failed'}{method ? ` · ${method.toUpperCase()}` : ''}</span>
}

export function AdminOrders() {
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const { data, isPending } = useAdminOrders(status, page)
  const pages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">Orders</h1>
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted">Status</span>
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="rounded-lg border border-line bg-surface px-3 py-2">
            {FILTERS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </label>
      </div>
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-surface-2 text-left text-xs tracking-wider text-muted uppercase">
            <tr><th className="p-3">Order</th><th className="p-3">Customer</th><th className="p-3">Placed</th><th className="p-3 text-right">Total</th><th className="p-3">Payment</th><th className="p-3">Status</th><th className="p-3">AWB</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isPending ? (
              <tr><td colSpan={7} className="p-4 text-muted">Loading…</td></tr>
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={7} className="p-4 text-muted">No orders with this status.</td></tr>
            ) : (
              data?.items.map((o) => (
                <tr key={o.number}>
                  <td className="p-3 font-mono text-xs">{o.number}</td>
                  <td className="p-3">{o.customer_email}</td>
                  <td className="p-3 text-muted tabular">{when.format(new Date(o.created_at))}</td>
                  <td className="p-3 text-right font-semibold tabular">{formatPaise(o.total)}</td>
                  <td className="p-3"><PaymentPill status={o.payment_status} method={o.payment_method} /></td>
                  <td className="p-3"><OrderStatus status={o.status} /></td>
                  <td className="p-3 font-mono text-xs">{o.awb_code ?? <span className="text-muted">—</span>}</td>
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
