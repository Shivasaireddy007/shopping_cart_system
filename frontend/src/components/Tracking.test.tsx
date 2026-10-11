import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Tracking } from './Tracking'

const wrap = (ui: React.ReactNode) =>
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>)

afterEach(() => vi.restoreAllMocks())

describe('Tracking', () => {
  it('shows the courier, AWB and timeline once a courier is assigned', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'shipped',
          courier_name: 'Delhivery',
          awb_code: 'AWB123',
          track_url: 'https://shiprocket.co/tracking/AWB123',
          events: [{ date: '2026-10-11 09:40', activity: 'In transit', location: 'Bengaluru hub' }],
        }),
        { headers: { 'Content-Type': 'application/json' } },
      ),
    )
    wrap(<Tracking number="ORD-1" status="shipped" />)

    expect(await screen.findByText('AWB123')).toBeInTheDocument()
    expect(screen.getByText('Delhivery')).toBeInTheDocument()
    expect(screen.getByText('In transit · Bengaluru hub')).toBeInTheDocument()
  })

  it('renders nothing for unpaid orders and does not call the API', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    const { container } = wrap(<Tracking number="ORD-1" status="pending_payment" />)

    expect(container).toBeEmptyDOMElement()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
