import { afterEach, describe, expect, it, vi } from 'vitest'

import { payWithRazorpay } from './razorpay'

const checkout = { key_id: 'rzp_test_key', order_id: 'order_ABC', amount: 120000, currency: 'INR' }

afterEach(() => {
  delete window.Razorpay
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
