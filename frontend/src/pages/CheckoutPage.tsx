import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import type { z } from 'zod'

import { ApiError } from '../api/client'
import { useCart, useCheckout } from '../hooks/queries'
import { usePayOrder } from '../hooks/usePayOrder'
import { formatPaise } from '../lib/money'
import { addressSchema } from '../lib/address'
import { INDIAN_STATES } from '../lib/states'
import { useAuth } from '../stores/auth'

type AddressInput = z.input<typeof addressSchema>
type Address = z.output<typeof addressSchema>

export function CheckoutPage() {
  const signedIn = useAuth((s) => s.accessToken !== null)
  const { data: cart } = useCart()
  const checkout = useCheckout()
  const { pay, paying, error: payError } = usePayOrder()
  const navigate = useNavigate()
  const form = useForm<AddressInput, unknown, Address>({ resolver: zodResolver(addressSchema) })

  if (!signedIn) return <Navigate to="/login" state={{ from: '/checkout' }} replace />
  if (cart && cart.items.length === 0 && !checkout.isSuccess) return <Navigate to="/cart" replace />

  const onSubmit = form.handleSubmit(async (address) => {
    try {
      const { order, razorpay } = await checkout.mutateAsync({ ...address, line2: address.line2 || null })
      await pay(razorpay, { number: order.number, name: address.name, phone: address.phone })
      navigate(`/orders/${order.number}`)
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 409
          ? `${e.message} Update your cart and try again.`
          : e instanceof Error
            ? e.message
            : 'Checkout failed'
      form.setError('root', { message })
    }
  })

  const err = form.formState.errors
  const input = 'rounded-lg border border-line bg-surface px-3 py-2 aria-invalid:border-crit'
  const busy = form.formState.isSubmitting || paying

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_320px]">
      <form onSubmit={onSubmit} noValidate className="grid content-start gap-4 rounded-xl bg-surface p-6" aria-labelledby="checkout-title">
        <h1 id="checkout-title" className="text-2xl font-extrabold">Delivery address</h1>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="name" label="Full name" error={err.name?.message}>
            <input id="name" autoComplete="name" className={input} aria-invalid={!!err.name} {...form.register('name')} />
          </Field>
          <Field id="phone" label="Mobile number" error={err.phone?.message}>
            <input id="phone" type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="98765 43210" className={`${input} tabular`} aria-invalid={!!err.phone} {...form.register('phone')} />
          </Field>
          <Field id="line1" label="Flat, house, street" error={err.line1?.message} className="sm:col-span-2">
            <input id="line1" autoComplete="address-line1" className={input} aria-invalid={!!err.line1} {...form.register('line1')} />
          </Field>
          <Field id="line2" label="Area, landmark (optional)" error={err.line2?.message} className="sm:col-span-2">
            <input id="line2" autoComplete="address-line2" className={input} {...form.register('line2')} />
          </Field>
          <Field id="city" label="City" error={err.city?.message}>
            <input id="city" autoComplete="address-level2" className={input} aria-invalid={!!err.city} {...form.register('city')} />
          </Field>
          <Field id="pincode" label="PIN code" error={err.pincode?.message}>
            <input id="pincode" inputMode="numeric" autoComplete="postal-code" className={`${input} tabular`} aria-invalid={!!err.pincode} {...form.register('pincode')} />
          </Field>
          <Field id="state" label="State" error={err.state?.message} className="sm:col-span-2">
            <select id="state" autoComplete="address-level1" defaultValue="" className={input} aria-invalid={!!err.state} {...form.register('state')}>
              <option value="" disabled>Choose a state</option>
              {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
        </div>
        {err.root || payError ? <p role="alert" className="rounded-lg bg-crit-soft px-3 py-2 text-crit">{err.root?.message ?? payError}</p> : null}
        <button type="submit" disabled={busy || !cart} className="rounded-lg bg-brand px-5 py-3 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
          {paying ? 'Waiting for payment…' : form.formState.isSubmitting ? 'Placing order…' : cart ? `Pay ${formatPaise(cart.total)}` : 'Pay'}
        </button>
        <p className="text-xs text-muted">Payments are processed by Razorpay. Your stock is held for 30 minutes while you pay.</p>
      </form>

      <aside className="grid content-start gap-2 rounded-xl bg-surface p-5 tabular">
        <h2 className="text-lg font-bold">Order summary</h2>
        {cart?.items.map((item) => (
          <div key={item.id} className="flex justify-between gap-3 text-sm">
            <span className="min-w-0">{item.name} <span className="text-muted">× {item.quantity}</span></span>
            <span>{formatPaise(item.line_total)}</span>
          </div>
        ))}
        <div className="mt-2 flex justify-between border-t border-line pt-2"><span>Shipping</span><span>{cart?.shipping_fee ? formatPaise(cart.shipping_fee) : 'Free'}</span></div>
        <div className="flex justify-between text-lg font-bold"><span>Total</span><span>{cart ? formatPaise(cart.total) : '–'}</span></div>
        <Link to="/cart" className="text-sm font-semibold text-brand">Edit cart</Link>
      </aside>
    </div>
  )
}

function Field(props: { id: string; label: string; error?: string; className?: string; children: React.ReactNode }) {
  return (
    <div className={`grid gap-1 ${props.className ?? ''}`}>
      <label htmlFor={props.id} className="text-sm font-semibold">{props.label}</label>
      {props.children}
      {props.error ? <p className="text-sm text-crit">{props.error}</p> : null}
    </div>
  )
}
