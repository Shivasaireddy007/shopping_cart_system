import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { Product } from '../api/client'
import { ProductCard } from './ProductCard'

const product: Product = {
  id: 1,
  sku: 'NIKE-PEG41',
  name: 'Nike Air Zoom Pegasus 41',
  slug: 'nike-air-zoom-pegasus-41',
  description: null,
  brand: 'Nike',
  price: 899900,
  mrp: 1099900,
  stock: 2,
  attributes: { color: 'black' },
  is_active: true,
  in_stock: true,
  category: { id: 1, name: 'Running Shoes', slug: 'running-shoes', parent_id: null },
}

const renderCard = (p: Product) =>
  render(
    <MemoryRouter>
      <ProductCard product={p} />
    </MemoryRouter>,
  )

describe('ProductCard', () => {
  it('links to the product and shows price, MRP and discount', () => {
    renderCard(product)

    expect(screen.getByRole('link')).toHaveAttribute('href', '/p/nike-air-zoom-pegasus-41')
    expect(screen.getByText('₹8,999')).toBeInTheDocument()
    expect(screen.getByText('₹10,999')).toBeInTheDocument()
    expect(screen.getByText('18% off')).toBeInTheDocument()
  })

  it('warns when stock is low and when it is out', () => {
    const { unmount } = renderCard(product)
    expect(screen.getByText('Only 2 left')).toBeInTheDocument()
    unmount()

    renderCard({ ...product, stock: 0, in_stock: false })
    expect(screen.getByText('Out of stock')).toBeInTheDocument()
  })
})
