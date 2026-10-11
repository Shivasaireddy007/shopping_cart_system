import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SearchPage } from './SearchPage'

function Location() {
  return <output data-testid="location">{useLocation().search}</output>
}

const response = (facets: unknown) =>
  new Response(JSON.stringify({ items: [], total: 0, page: 1, per_page: 24, facets, engine: facets ? 'opensearch' : 'database' }), {
    headers: { 'Content-Type': 'application/json' },
  })

function renderAt(url: string) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/search" element={<><SearchPage /><Location /></>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.restoreAllMocks())

describe('SearchPage', () => {
  it('shows facet counts and adds a ticked brand to the URL and the API query', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input instanceof Request ? input.url : input)
      if (url.includes('/categories')) return new Response('[]', { headers: { 'Content-Type': 'application/json' } })
      return response({ brand: [{ value: 'Nike', count: 7 }, { value: 'Puma', count: 3 }], price: [] })
    })
    renderAt('/search?q=shoes')

    const nike = await screen.findByRole('checkbox', { name: /Nike/ })
    expect(screen.getByText('7')).toBeInTheDocument()

    await userEvent.click(nike)

    expect(screen.getByTestId('location')).toHaveTextContent('brand=Nike')
    const urls = fetchMock.mock.calls.map(([input]) => String(input instanceof Request ? input.url : input))
    expect(urls.some((u) => u.includes('/api/v1/search') && u.includes('brand=Nike'))).toBe(true)
  })

  it('explains limited filters when search falls back to the database', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input instanceof Request ? input.url : input)
      if (url.includes('/categories')) return new Response('[]', { headers: { 'Content-Type': 'application/json' } })
      return response(null)
    })
    renderAt('/search?q=shoes')

    expect(await screen.findByText(/Filters are limited right now/)).toBeInTheDocument()
  })
})
