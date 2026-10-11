import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ApiError } from '../api/client'
import { Price } from '../components/Price'
import { ProductArt } from '../components/ProductArt'
import { useAddToCart, useProduct } from '../hooks/queries'
import { useAuth } from '../stores/auth'

export function ProductPage() {
  const { slug = '' } = useParams()
  const { data: product, isPending, error } = useProduct(slug)
  const [quantity, setQuantity] = useState(1)
  const addToCart = useAddToCart()
  const signedIn = useAuth((s) => s.accessToken !== null)
  const navigate = useNavigate()
  const location = useLocation()

  if (isPending) return <p className="text-muted">Loading…</p>
  if (error) {
    return (
      <p className="rounded-lg bg-surface p-6">
        {error instanceof ApiError && error.status === 404 ? 'This product is no longer available.' : "Couldn't load this product."}{' '}
        <Link to="/" className="font-semibold text-brand">Back to the shop</Link>
      </p>
    )
  }

  const add = () => {
    if (!signedIn) {
      navigate('/login', { state: { from: location.pathname } })
      return
    }
    addToCart.mutate({ productId: product.id, quantity })
  }

  return (
    <div className="grid gap-8 rounded-xl bg-surface p-6 md:grid-cols-[1.1fr_1fr]">
      <ProductArt product={product} className="aspect-square" />
      <div className="grid content-start gap-4">
        <div className="text-sm text-muted">
          <Link to={`/?category=${product.category.slug}`} className="hover:text-brand">{product.category.name}</Link> · {product.brand}
        </div>
        <h1 className="text-3xl font-extrabold leading-tight">{product.name}</h1>
        <Price price={product.price} mrp={product.mrp} size="lg" />
        <p className="text-sm text-muted">Inclusive of all taxes · Free delivery above ₹999</p>
        {product.description ? <p className="max-w-prose leading-relaxed">{product.description}</p> : null}

        {product.stock === 0 ? (
          <p className="font-semibold text-muted">Out of stock</p>
        ) : (
          <>
            {product.stock <= 5 ? <p className="font-semibold text-warn">Only {product.stock} left in stock</p> : null}
            <div className="flex flex-wrap items-center gap-3">
              <label htmlFor="qty" className="text-sm font-semibold">Quantity</label>
              <select id="qty" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="rounded-lg border border-line bg-surface px-3 py-2">
                {Array.from({ length: Math.min(product.stock, 10) }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <button type="button" onClick={add} disabled={addToCart.isPending} className="rounded-lg bg-brand px-5 py-2.5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
                {addToCart.isPending ? 'Adding…' : 'Add to cart'}
              </button>
            </div>
          </>
        )}
        {addToCart.isSuccess ? (
          <p className="rounded-lg bg-good-soft px-3 py-2 font-semibold text-good">
            Added to your cart. <Link to="/cart" className="underline">View cart</Link>
          </p>
        ) : null}
        {addToCart.error ? <p className="rounded-lg bg-crit-soft px-3 py-2 text-crit">{addToCart.error.message}</p> : null}
        <p className="font-mono text-xs text-muted">SKU {product.sku}</p>
      </div>
    </div>
  )
}
