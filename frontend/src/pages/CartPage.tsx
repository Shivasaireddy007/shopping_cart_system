import { Link, Navigate } from 'react-router-dom'

import { formatPaise } from '../lib/money'
import { useCart, useRemoveCartItem, useUpdateCartItem } from '../hooks/queries'
import { useAuth } from '../stores/auth'

export function CartPage() {
  const signedIn = useAuth((s) => s.accessToken !== null)
  const { data: cart, isPending } = useCart()
  const update = useUpdateCartItem()
  const remove = useRemoveCartItem()

  if (!signedIn) return <Navigate to="/login" state={{ from: '/cart' }} replace />
  if (isPending || !cart) return <p className="text-muted">Loading your cart…</p>

  if (cart.items.length === 0) {
    return (
      <div className="rounded-xl bg-surface p-8 text-center">
        <h1 className="text-2xl font-extrabold">Your cart is empty</h1>
        <Link to="/" className="mt-3 inline-block font-semibold text-brand">Browse products</Link>
      </div>
    )
  }

  const error = update.error ?? remove.error

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_320px]">
      <section className="grid content-start gap-3 rounded-xl bg-surface p-5">
        <h1 className="text-2xl font-extrabold">Cart</h1>
        {error ? <p className="rounded-lg bg-warn-soft px-3 py-2 text-warn">{error.message}</p> : null}
        <ul className="divide-y divide-line">
          {cart.items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center gap-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{item.name}</p>
                <p className="font-mono text-xs text-muted">{item.sku} · {formatPaise(item.unit_price)} each</p>
              </div>
              <label className="sr-only" htmlFor={`qty-${item.id}`}>Quantity for {item.name}</label>
              <select
                id={`qty-${item.id}`}
                value={item.quantity}
                onChange={(e) => update.mutate({ itemId: item.id, quantity: Number(e.target.value) })}
                className="rounded-lg border border-line bg-surface px-2 py-1.5"
              >
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <span className="w-24 text-right font-semibold tabular">{formatPaise(item.line_total)}</span>
              <button type="button" onClick={() => remove.mutate(item.id)} className="text-sm text-muted hover:text-crit">
                Remove
              </button>
            </li>
          ))}
        </ul>
      </section>
      <aside className="grid content-start gap-2 rounded-xl bg-surface p-5 tabular">
        <h2 className="text-lg font-bold">Price details</h2>
        <div className="flex justify-between"><span>Subtotal</span><span>{formatPaise(cart.subtotal)}</span></div>
        <div className="flex justify-between">
          <span>Shipping</span>
          <span className={cart.shipping_fee === 0 ? 'font-semibold text-good' : ''}>{cart.shipping_fee === 0 ? 'Free' : formatPaise(cart.shipping_fee)}</span>
        </div>
        <div className="mt-1 flex justify-between border-t border-line pt-2 text-lg font-bold"><span>Total</span><span>{formatPaise(cart.total)}</span></div>
        <button type="button" disabled className="mt-2 rounded-lg bg-brand px-4 py-2.5 font-semibold text-white opacity-60" title="Checkout arrives with the Razorpay integration">
          Checkout (coming soon)
        </button>
        <p className="text-xs text-muted">Orders under ₹999 pay ₹49 shipping.</p>
      </aside>
    </div>
  )
}
