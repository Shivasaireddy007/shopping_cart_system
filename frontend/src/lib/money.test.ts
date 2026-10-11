import { describe, expect, it } from 'vitest'

import { discountPercent, formatPaise } from './money'

describe('formatPaise', () => {
  it('formats paise as whole rupees with Indian digit grouping', () => {
    expect(formatPaise(899900)).toBe('₹8,999')
    expect(formatPaise(10999900)).toBe('₹1,09,999')
    expect(formatPaise(4900)).toBe('₹49')
  })
})

describe('discountPercent', () => {
  it('rounds the discount down', () => {
    expect(discountPercent(899900, 1099900)).toBe(18)
  })

  it('returns null without a real discount', () => {
    expect(discountPercent(1000, null)).toBeNull()
    expect(discountPercent(1000, 1000)).toBeNull()
  })
})
