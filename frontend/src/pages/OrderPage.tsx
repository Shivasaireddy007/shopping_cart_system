import { Link, useParams } from 'react-router-dom'

import { OrderStatus } from '../components/OrderStatus'
import { Tracking } from '../components/Tracking'
import { useCancelOrder, useOrder, useRetryPayment } from '../hooks/queries'
import { usePayOrder } from '../hooks/usePayOrder'
import { formatPaise } from '../lib/money'

const dateTime = new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' })

export function OrderPage() {
  const { number = '' } = useParams()
  const { data: order, isPending, error } = useOrder(number)
  const cancel = useCancelOrder()
  const retry = useRetryPayment()
  const { pay, paying, error: payError } = usePayOrder()

  if (isPending) return <p className="text-muted">Loading order…</p>
  if (error || !order) {
    return (
      <p className="rounded-lg bg-surface p-6">
        We couldn't find that order. <Link to="/orders" className="font-semibold text-brand">See your orders</Link>
      </p>
    )
  }

  const payNow = async () => {
    const checkout = await retry.mutateAsync(order.number)
    await pay(checkout, { number: order.number, name: order.shipping_address.name, phone: order.shipping_address.phone })
  }

  const awaiting = order.status === 'pending_payment'
  const address = order.shipping_address
  const actionError = payError ?? cancel.error?.message ?? retry.error?.message

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_320px]">
      <section className="grid content-start gap-4 rounded-xl bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-sm text-muted">{order.number}</p>
            <h1 className="text-2xl font-extrabold">
              {awaiting ? 'Complete your payment' : order.status === 'cancelled' ? 'Order cancelled' : 'Thank you for your order'}
            </h1>
            <p className="text-sm text-muted">Placed {dateTime.format(new Date(order.created_at))}</p>
          </div>
          <OrderStatus status={order.status} />
        </div>

        {awaiting ? (
          <div className="grid gap-3 rounded-lg bg-warn-soft p-4">
            <p className="text-sm">This order isn't paid yet. We'll hold the stock for 30 minutes, then cancel it.</p>
            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={payNow} disabled={paying || retry.isPending} className="rounded-lg bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
                {paying ? 'Waiting for payment…' : `Pay ${formatPaise(order.total)}`}
              </button>
              <button type="button" onClick={() => cancel.mutate(order.number)} disabled={cancel.isPending} className="rounded-lg border border-line bg-surface px-4 py-2 font-semibold hover:border-crit hover:text-crit">
                Cancel order
              </button>
            </div>
          </div>
        ) : null}
        {actionError ? <p role="alert" className="rounded-lg bg-crit-soft px-3 py-2 text-crit">{actionError}</p> : null}

        <ul className="divide-y divide-line">
          {order.items.map((item) => (
            <li key={item.sku} className="flex flex-wrap justify-between gap-3 py-3">
              <div>
                <p className="font-semibold">{item.name}</p>
                <p className="font-mono text-xs text-muted">{item.sku} · {formatPaise(item.unit_price)} × {item.quantity}</p>
              </div>
              <span className="font-semibold tabular">{formatPaise(item.line_total)}</span>
            </li>
          ))}
        </ul>
      </section>

      <aside className="grid content-start gap-4">
        <Tracking number={order.number} status={order.status} />
        <div className="grid gap-2 rounded-xl bg-surface p-5 tabular">
          <h2 className="text-lg font-bold">Payment</h2>
          <div className="flex justify-between"><span>Subtotal</span><span>{formatPaise(order.subtotal)}</span></div>
          <div className="flex justify-between"><span>Shipping</span><span>{order.shipping_fee ? formatPaise(order.shipping_fee) : 'Free'}</span></div>
          <div className="flex justify-between border-t border-line pt-2 text-lg font-bold"><span>Total</span><span>{formatPaise(order.total)}</span></div>
          {order.paid_at ? <p className="text-sm text-good">Paid {dateTime.format(new Date(order.paid_at))}</p> : null}
        </div>
        <div className="grid gap-1 rounded-xl bg-surface p-5 text-sm">
          <h2 className="text-lg font-bold">Delivering to</h2>
          <p className="font-semibold">{address.name} · <span className="tabular">{address.phone}</span></p>
          <p className="text-muted">{address.line1}{address.line2 ? `, ${address.line2}` : ''}</p>
          <p className="text-muted">{address.city}, {address.state} {address.pincode}</p>
        </div>
      </aside>
    </div>
  )
}
