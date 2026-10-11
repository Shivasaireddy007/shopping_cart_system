import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RevenueChart } from './RevenueChart'

const days = [
  { date: '2026-10-05', revenue: 0, orders: 0 },
  { date: '2026-10-06', revenue: 1250000, orders: 4 },
  { date: '2026-10-07', revenue: 980000, orders: 3 },
  { date: '2026-10-08', revenue: 2410000, orders: 7 },
  { date: '2026-10-09', revenue: 1800000, orders: 5 },
  { date: '2026-10-10', revenue: 3020000, orders: 9 },
  { date: '2026-10-11', revenue: 2936000, orders: 1 },
]

describe('RevenueChart', () => {
  it('draws a bar per day with revenue and skips empty days', () => {
    const { container } = render(<RevenueChart days={days} />)

    expect(container.querySelectorAll('path')).toHaveLength(6)
    expect(screen.getByText('Today')).toBeInTheDocument()
  })

  it('labels the axis in Indian units on a clean scale', () => {
    render(<RevenueChart days={days} />)

    // Highest day ₹30,200 rounds up to a ₹50k axis with a ₹25k midline.
    expect(screen.getByText('₹50k')).toBeInTheDocument()
    expect(screen.getByText('₹25k')).toBeInTheDocument()
  })

  it('shows a tooltip on keyboard focus and has a table for screen readers', () => {
    render(<RevenueChart days={days} />)

    fireEvent.focus(screen.getByRole('button', { name: /₹30,200 from 9 orders/ }))
    expect(screen.getByRole('status')).toHaveTextContent('₹30,200 · 9 orders')
    expect(screen.getAllByRole('row')).toHaveLength(8)
  })
})
