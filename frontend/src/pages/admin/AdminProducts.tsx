import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useAdminProducts, useArchiveProduct } from '../../hooks/queries'
import { formatPaise } from '../../lib/money'

export function AdminProducts() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const { data, isPending } = useAdminProducts(search, page)
  const archive = useArchiveProduct()
  const pages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">Products</h1>
        <div className="flex gap-2">
          <label htmlFor="search" className="sr-only">Search by SKU or name</label>
          <input
            id="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="SKU or name"
            className="rounded-lg border border-line bg-surface px-3 py-2 text-sm"
          />
          <Link to="/admin/products/new" className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-dark">
            New product
          </Link>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-surface-2 text-left text-xs tracking-wider text-muted uppercase">
            <tr>
              <th className="p-3">Product</th>
              <th className="p-3">SKU</th>
              <th className="p-3 text-right">Price</th>
              <th className="p-3 text-right">Stock</th>
              <th className="p-3">Status</th>
              <th className="p-3"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {isPending ? (
              <tr><td colSpan={6} className="p-4 text-muted">Loading…</td></tr>
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={6} className="p-4 text-muted">No products match “{search}”.</td></tr>
            ) : (
              data?.items.map((p) => (
                <tr key={p.id}>
                  <td className="p-3 font-semibold">{p.name}</td>
                  <td className="p-3 font-mono text-xs">{p.sku}</td>
                  <td className="p-3 text-right tabular">{formatPaise(p.price)}</td>
                  <td className={`p-3 text-right tabular ${p.stock <= 3 ? 'font-bold text-crit' : ''}`}>{p.stock}</td>
                  <td className="p-3">
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${p.is_active ? 'bg-good-soft text-good' : 'bg-surface-2 text-muted'}`}>
                      {p.is_active ? 'Active' : 'Archived'}
                    </span>
                  </td>
                  <td className="p-3 text-right whitespace-nowrap">
                    <Link to={`/admin/products/${p.id}`} state={{ product: p }} className="font-semibold text-brand">Edit</Link>
                    {p.is_active ? (
                      <button type="button" onClick={() => archive.mutate(p.id)} className="ml-3 text-muted hover:text-crit">
                        Archive
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pages > 1 ? (
        <nav className="flex items-center gap-3 text-sm" aria-label="Pages">
          <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)} className="rounded-lg border border-line bg-surface px-3 py-1.5 disabled:opacity-40">Previous</button>
          <span className="text-muted tabular">Page {page} of {pages}</span>
          <button type="button" disabled={page === pages} onClick={() => setPage(page + 1)} className="rounded-lg border border-line bg-surface px-3 py-1.5 disabled:opacity-40">Next</button>
        </nav>
      ) : null}
    </div>
  )
}
