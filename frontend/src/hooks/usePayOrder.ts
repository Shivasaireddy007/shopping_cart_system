import { useState } from 'react'

import type { RazorpayCheckout } from '../api/client'
import { payWithRazorpay } from '../lib/razorpay'
import { useVerifyPayment } from './queries'

/** Opens Razorpay for an order and confirms the payment with the backend. */
export function usePayOrder() {
  const verify = useVerifyPayment()
  const [error, setError] = useState<string | null>(null)
  const [paying, setPaying] = useState(false)

  const pay = async (checkout: RazorpayCheckout, order: { number: string; name?: string; phone?: string }) => {
    setError(null)
    setPaying(true)
    try {
      const result = await payWithRazorpay(checkout, { orderNumber: order.number, name: order.name, phone: order.phone })
      if (result) await verify.mutateAsync({ number: order.number, result })
      return result !== null
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Payment failed')
      return false
    } finally {
      setPaying(false)
    }
  }

  return { pay, paying, error }
}
