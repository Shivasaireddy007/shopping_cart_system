import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { OversellExperiment } from './OversellExperiment'

const wrap = (ui: React.ReactNode) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>)

function reply(locked: boolean, soldBuyers: number, finalStock: number) {
  const attempts = Array.from({ length: 10 }, (_, i) => ({ buyer: i + 1, sold: i < soldBuyers, ms: 40 + i }))
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ locked, units: 3, attempts, sold: soldBuyers, final_stock: finalStock, ms: 62 }), {
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

afterEach(() => vi.restoreAllMocks())

describe('OversellExperiment', () => {
  it('shows every unit accounted for with the real checkout', async () => {
    reply(true, 3, 0)
    wrap(<OversellExperiment available />)

    screen.getByRole('button', { name: 'Run the real checkout' }).click()

    expect(await screen.findByText(/3 of 10 bought, 7 were told it's sold out, and the stock is 0/)).toBeInTheDocument()
    expect(screen.getAllByText('Sold out')).toHaveLength(7)
  })

  it('shows the oversell with the naive code', async () => {
    reply(false, 10, 2)
    wrap(<OversellExperiment available />)

    screen.getByRole('button', { name: 'Run naive code without a lock' }).click()

    expect(await screen.findByText(/Oversold by 7/)).toBeInTheDocument()
    expect((vi.mocked(fetch).mock.calls[0][0] as Request).url).toContain('locked=false')
  })

  it('points to the test suite where the experiment is not available', () => {
    wrap(<OversellExperiment available={false} />)
    expect(screen.getByText('pytest -m concurrency')).toBeInTheDocument()
  })
})
