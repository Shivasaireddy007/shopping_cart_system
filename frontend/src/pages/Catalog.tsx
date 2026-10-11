import { useSearchParams } from 'react-router-dom'

import { ProductCard } from '../components/ProductCard'
import { type ProductQuery, useCategories, useProducts } from '../hooks/queries'

const BRANDS = ['Adidas', 'Bata', 'Campus', 'Nike', 'Puma', 'Reebok', 'Sparx', 'Woodland']
const PRICE_RANGES = [
  { label: 'Under ₹500', min: undefined, max: 50000 },
  { label: '₹500 – 1,000', min: 50000, max: 100000 },
  { label: '₹1,000 – 2,500', min: 100000, max: 250000 },
  { label: '₹2,500 – 5,000', min: 250000, max: 500000 },
  { label: 'Over ₹5,000', min: 500000, max: undefined },
]
const SORTS: { value: NonNullable<ProductQuery['sort']>; label: string }[] = [
  { value: 'newest', label: 'Newest' },
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
  { value: 'name', label: 'Name' },
]
const PER_PAGE = 24

export function Catalog() {
  const [params, setParams] = useSearchParams()
  const { data: categories } = useCategories()

  const num = (key: string) => (params.get(key) ? Number(params.get(key)) : undefined)
  const query: ProductQuery = {
    category: params.get('category') ?? undefined,
    brand: params.get('brand') ?? undefined,
    min_price: num('min_price'),
    max_price: num('max_price'),
    in_stock: params.get('in_stock') === 'true',
    sort: (params.get('sort') as ProductQuery['sort']) ?? 'newest',
    page: num('page') ?? 1,
    per_page: PER_PAGE,
  }
  const { data, isPending, isError, isPlaceholderData } = useProducts(query)

  /** Changing a filter resets to page 1; empty values are removed from the URL. */
  const update = (changes: Record<string, string | number | undefined>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value === undefined || value === '') next.delete(key)
      else next.set(key, String(value))
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / PER_PAGE)) : 1
  const activeRange = PRICE_RANGES.find((r) => r.min === query.min_price && r.max === query.max_price)

  return (
    <div className="grid gap-6 md:grid-cols-[200px_1fr]">
      <aside className="grid content-start gap-6 text-sm" aria-label="Filters">
        <FilterGroup title="Category">
          <Choice label="All" checked={!query.category} onChange={() => update({ category: undefined })} name="category" />
          {categories?.map((c) => (
            <Choice key={c.id} label={c.name} checked={query.category === c.slug} onChange={() => update({ category: c.slug })} name="category" />
          ))}
        </FilterGroup>
        <FilterGroup title="Brand">
          <Choice label="All" checked={!query.brand} onChange={() => update({ brand: undefined })} name="brand" />
          {BRANDS.map((b) => (
            <Choice key={b} label={b} checked={query.brand === b} onChange={() => update({ brand: b })} name="brand" />
          ))}
        </FilterGroup>
        <FilterGroup title="Price">
          <Choice label="Any" checked={!activeRange} onChange={() => update({ min_price: undefined, max_price: undefined })} name="price" />
          {PRICE_RANGES.map((r) => (
            <Choice key={r.label} label={r.label} checked={activeRange === r} onChange={() => update({ min_price: r.min, max_price: r.max })} name="price" />
          ))}
        </FilterGroup>
        <label className="flex items-center gap-2 font-semibold">
          <input
            type="checkbox"
            checked={query.in_stock}
            onChange={(e) => update({ in_stock: e.target.checked ? 'true' : undefined })}
            className="size-4 accent-brand"
          />
          In stock only
        </label>
      </aside>

      <section className="grid content-start gap-4" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-extrabold">
            {categories?.find((c) => c.slug === query.category)?.name ?? 'All products'}
          </h1>
          <div className="flex items-center gap-3 text-sm">
            {data ? <span className="text-muted tabular">{data.total.toLocaleString('en-IN')} results</span> : null}
            <label className="sr-only" htmlFor="sort">Sort by</label>
            <select
              id="sort"
              value={query.sort}
              onChange={(e) => update({ sort: e.target.value })}
              className="rounded-lg border border-line bg-surface px-3 py-2"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        {isError ? (
          <p className="rounded-lg bg-crit-soft p-4 text-crit">Couldn't load products. Check that the API is running and try again.</p>
        ) : isPending ? (
          <p className="text-muted">Loading products…</p>
        ) : data.items.length === 0 ? (
          <p className="rounded-lg bg-surface p-6 text-muted">No products match these filters. Try removing one.</p>
        ) : (
          <div className={`grid grid-cols-2 gap-4 lg:grid-cols-3 ${isPlaceholderData ? 'opacity-60' : ''}`}>
            {data.items.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}

        {data && pages > 1 ? (
          <nav className="flex items-center justify-center gap-3 pt-2 text-sm" aria-label="Pages">
            <button type="button" disabled={query.page === 1} onClick={() => update({ page: (query.page ?? 1) - 1 })} className="rounded-lg border border-line bg-surface px-3 py-2 disabled:opacity-40">
              Previous
            </button>
            <span className="text-muted tabular">Page {query.page} of {pages}</span>
            <button type="button" disabled={query.page === pages} onClick={() => update({ page: (query.page ?? 1) + 1 })} className="rounded-lg border border-line bg-surface px-3 py-2 disabled:opacity-40">
              Next
            </button>
          </nav>
        ) : null}
      </section>
    </div>
  )
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="grid gap-1.5">
      <legend className="mb-1 text-xs font-bold tracking-widest text-muted uppercase">{title}</legend>
      {children}
    </fieldset>
  )
}

function Choice(props: { label: string; checked: boolean; onChange: () => void; name: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-2">
      <input type="radio" name={props.name} checked={props.checked} onChange={props.onChange} className="size-4 accent-brand" />
      {props.label}
    </label>
  )
}
