import { Link } from 'react-router-dom'

import type { Product } from '../api/client'
import { Price } from './Price'
import { ProductArt } from './ProductArt'

export function ProductCard({ product }: { product: Product }) {
  return (
    <Link to={`/p/${product.slug}`} className="group grid gap-1.5 rounded-lg focus-visible:outline-2">
      <div className="relative">
        <ProductArt product={product} className="aspect-[4/3] transition group-hover:brightness-95" />
        {product.stock === 0 ? (
          <span className="absolute top-2 left-2 rounded-full bg-surface-2 px-2 py-1 text-xs font-semibold text-muted">
            Out of stock
          </span>
        ) : product.stock <= 3 ? (
          <span className="absolute top-2 left-2 rounded-full bg-crit-soft px-2 py-1 text-xs font-semibold text-crit">
            Only {product.stock} left
          </span>
        ) : null}
      </div>
      <span className="text-xs text-muted">{product.brand}</span>
      <span className="leading-snug font-semibold group-hover:text-brand">{product.name}</span>
      <Price price={product.price} mrp={product.mrp} />
    </Link>
  )
}
