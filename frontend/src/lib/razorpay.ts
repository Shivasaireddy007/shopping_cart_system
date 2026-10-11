import type { RazorpayCheckout } from '../api/client'

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
