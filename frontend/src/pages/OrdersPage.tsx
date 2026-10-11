import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { OrderStatus } from '../components/OrderStatus'
import { useOrders } from '../hooks/queries'
import { formatPaise } from '../lib/money'
import { useAuth } from '../stores/auth'

const dateFormat = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

export function OrdersPage() {
  const signedIn = useAuth((s) => s.accessToken !== null)
  const [page, setPage] = useState(1)
  const { data, isPending } = useOrders(page)

  if (!signedIn) return <Navigate to="/login" state={{ from: '/orders' }} replace />
  if (isPending || !data) return <p className="text-muted">Loading your orders…</p>

  if (data.total === 0) {
    return (
      <div className="rounded-xl bg-surface p-8 text-center">
        <h1 className="text-2xl font-extrabold">No orders yet</h1>
        <Link to="/" className="mt-3 inline-block font-semibold text-brand">Start shopping</Link>
      </div>
    )
  }

  const pages = Math.ceil(data.total / data.per_page)

  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-extrabold">Your orders</h1>
      <ul className="grid gap-3">
        {data.items.map((order) => (
          <li key={order.number}>
            <Link to={`/orders/${order.number}`} className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-xl bg-surface p-4 hover:ring-2 hover:ring-brand/30">
              <span className="font-mono text-sm font-semibold">{order.number}</span>
              <span className="text-sm text-muted">{dateFormat.format(new Date(order.created_at))}</span>
              <span className="text-sm text-muted">{order.items.reduce((n, i) => n + i.quantity, 0)} item(s)</span>
              <span className="ml-auto font-bold tabular">{formatPaise(order.total)}</span>
              <OrderStatus status={order.status} />
            </Link>
          </li>
        ))}
      </ul>
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
