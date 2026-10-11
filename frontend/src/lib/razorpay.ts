import { api, type RazorpayCheckout, unwrap } from '../api/client'
import { formatPaise } from './money'

export type RazorpaySuccess = {
  razorpay_payment_id: string
  razorpay_order_id: string
  razorpay_signature: string
}

type RazorpayOptions = {
  key: string
  amount: number
  currency: string
  order_id: string
  name: string
  description: string
  prefill: { name?: string; contact?: string; email?: string }
  theme: { color: string }
  handler: (response: RazorpaySuccess) => void
  modal: { ondismiss: () => void }
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => { open: () => void }
  }
}

/** Key id the server sends when it runs the public demo without a Razorpay account. */
export const DEMO_KEY_ID = 'rzp_demo'

const SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js'
let loading: Promise<void> | null = null

function loadScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  loading ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = SCRIPT_URL
    script.onload = () => resolve()
    script.onerror = () => {
      loading = null
      reject(new Error("Couldn't load Razorpay. Check your connection and try again."))
    }
    document.body.appendChild(script)
  })
  return loading
}

/**
 * Opens Razorpay Checkout. Resolves with the signed result on payment, or null if the
 * shopper closes the window (the order stays unpaid and can be paid later).
 */
export async function payWithRazorpay(
  checkout: RazorpayCheckout,
  details: { orderNumber: string; name?: string; phone?: string },
): Promise<RazorpaySuccess | null> {
  if (checkout.key_id === DEMO_KEY_ID) return payInDemo(checkout, details.orderNumber)
  await loadScript()
  const Razorpay = window.Razorpay
  if (!Razorpay) throw new Error("Couldn't load Razorpay.")

  return new Promise((resolve) => {
    new Razorpay({
      key: checkout.key_id,
      amount: checkout.amount,
      currency: checkout.currency,
      order_id: checkout.order_id,
      name: 'Shopping Cart',
      description: `Order ${details.orderNumber}`,
      prefill: { name: details.name, contact: details.phone },
      theme: { color: '#22307A' },
      handler: resolve,
      modal: { ondismiss: () => resolve(null) },
    }).open()
  })
}

/**
 * The public demo has no Razorpay account. After the shopper confirms, the server signs a
 * simulated payment, which then goes through the same verification as a real one.
 */
async function payInDemo(checkout: RazorpayCheckout, orderNumber: string): Promise<RazorpaySuccess | null> {
  if (!(await confirmDemoPayment(formatPaise(checkout.amount), orderNumber))) return null
  const signed = await unwrap(
    api.POST('/api/v1/orders/{number}/demo-payment', { params: { path: { number: orderNumber } } }),
  )
  return { ...signed, razorpay_order_id: checkout.order_id }
}

function confirmDemoPayment(amount: string, orderNumber: string): Promise<boolean> {
  return new Promise((resolve) => {
    const dialog = document.createElement('dialog')
    dialog.className = 'm-auto w-[min(24rem,calc(100%-2rem))] rounded-lg bg-surface p-6 text-ink shadow-xl backdrop:bg-ink/50'
    dialog.setAttribute('aria-labelledby', 'demo-payment-title')

    const title = Object.assign(document.createElement('h2'), {
      id: 'demo-payment-title',
      className: 'text-lg font-bold',
      textContent: `Pay ${amount}`,
    })
    const note = Object.assign(document.createElement('p'), {
      className: 'mt-2 text-sm text-muted',
      textContent: `Order ${orderNumber}. This demo has no Razorpay account, so the payment is simulated and no money moves.`,
    })
    const pay = Object.assign(document.createElement('button'), {
      type: 'button',
      className: 'rounded-md bg-brand px-4 py-2 font-semibold text-white hover:bg-brand-dark',
      textContent: 'Pay (demo)',
    })
    const cancel = Object.assign(document.createElement('button'), {
      type: 'button',
      className: 'rounded-md px-4 py-2 font-semibold text-muted hover:text-ink',
      textContent: 'Cancel',
    })
    const actions = Object.assign(document.createElement('div'), { className: 'mt-6 flex justify-end gap-2' })
    actions.append(cancel, pay)
    dialog.append(title, note, actions)

    const finish = (paid: boolean) => {
      dialog.remove()
      resolve(paid)
    }
    pay.addEventListener('click', () => finish(true))
    cancel.addEventListener('click', () => finish(false))
    dialog.addEventListener('cancel', () => finish(false)) // Escape key

    document.body.append(dialog)
    if (typeof dialog.showModal === 'function') dialog.showModal()
    else dialog.setAttribute('open', '')
    pay.focus()
  })
}
