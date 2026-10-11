import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DEMO_KEY_ID, payWithRazorpay } from './razorpay'

const checkout = { key_id: 'rzp_test_key', order_id: 'order_ABC', amount: 120000, currency: 'INR' }

afterEach(() => {
  delete window.Razorpay
  vi.restoreAllMocks()
})

describe('payWithRazorpay', () => {
  it('opens Razorpay with the order and resolves with the signed result', async () => {
    const open = vi.fn()
    const Razorpay = vi.fn(function (this: { open: () => void }, options) {
      this.open = () => {
        open()
        options.handler({ razorpay_payment_id: 'pay_1', razorpay_order_id: 'order_ABC', razorpay_signature: 'sig' })
      }
    })
    window.Razorpay = Razorpay as unknown as typeof window.Razorpay

    const result = await payWithRazorpay(checkout, { orderNumber: 'ORD-1', name: 'Asha', phone: '9876543210' })

    expect(result?.razorpay_payment_id).toBe('pay_1')
    expect(Razorpay).toHaveBeenCalledWith(
      expect.objectContaining({ key: 'rzp_test_key', order_id: 'order_ABC', amount: 120000, prefill: { name: 'Asha', contact: '9876543210' } }),
    )
    expect(open).toHaveBeenCalledOnce()
  })

  it('resolves with null when the shopper closes the window', async () => {
    window.Razorpay = vi.fn(function (this: { open: () => void }, options) {
      this.open = () => options.modal.ondismiss()
    }) as unknown as typeof window.Razorpay

    expect(await payWithRazorpay(checkout, { orderNumber: 'ORD-1' })).toBeNull()
  })
})

describe('payWithRazorpay in the public demo', () => {
  const demo = { ...checkout, key_id: DEMO_KEY_ID }

  it('asks to confirm, then returns the payment the server signed', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ razorpay_payment_id: 'pay_demo1', razorpay_signature: 'sig' }), {
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const paying = payWithRazorpay(demo, { orderNumber: 'ORD-1' })
    expect(screen.getByRole('heading', { name: 'Pay ₹1,200' })).toBeInTheDocument()
    screen.getByRole('button', { name: 'Pay (demo)' }).click()

    expect(await paying).toEqual({ razorpay_payment_id: 'pay_demo1', razorpay_signature: 'sig', razorpay_order_id: 'order_ABC' })
    expect((fetch.mock.calls[0][0] as Request).url).toMatch(/\/api\/v1\/orders\/ORD-1\/demo-payment$/)
    expect(window.Razorpay).toBeUndefined()
  })

  it('resolves with null when the shopper cancels', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch')

    const paying = payWithRazorpay(demo, { orderNumber: 'ORD-1' })
    screen.getByRole('button', { name: 'Cancel' }).click()

    expect(await paying).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Pay (demo)' })).not.toBeInTheDocument()
  })
})
