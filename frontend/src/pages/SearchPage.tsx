import { useSearchParams } from 'react-router-dom'

import { ProductCard } from '../components/ProductCard'
import { type SearchQuery, useCategories, useSearch } from '../hooks/queries'

const FACETS = [
  { key: 'brand', title: 'Brand' },
  { key: 'category', title: 'Category' },
  { key: 'color', title: 'Colour' },
  { key: 'size', title: 'Size' },
] as const

const PRICE_RANGES: Record<string, { label: string; min?: number; max?: number }> = {
  'under-500': { label: 'Under ₹500', max: 50000 },
  '500-1000': { label: '₹500 – 1,000', min: 50000, max: 100000 },
  '1000-2500': { label: '₹1,000 – 2,500', min: 100000, max: 250000 },
  '2500-5000': { label: '₹2,500 – 5,000', min: 250000, max: 500000 },
  'over-5000': { label: 'Over ₹5,000', min: 500000 },
}

const SORTS: { value: NonNullable<SearchQuery['sort']>; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'newest', label: 'Newest' },
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
]

const SWATCHES: Record<string, string> = {
  black: '#1d1f24', white: '#f4f4f2', red: '#c8342c', blue: '#2f5bd3', green: '#3e8a52', grey: '#7c8a92',
}

export function SearchPage() {
  const [params, setParams] = useSearchParams()
  const { data: categories } = useCategories()
  const num = (key: string) => (params.get(key) ? Number(params.get(key)) : undefined)

  const query: SearchQuery = {
    q: params.get('q') ?? undefined,
    brand: params.getAll('brand'),
    category: params.getAll('category'),
    color: params.getAll('color'),
    size: params.getAll('size'),
    min_price: num('min_price'),
    max_price: num('max_price'),
    in_stock: params.get('in_stock') === 'true',
    sort: (params.get('sort') as SearchQuery['sort']) ?? 'relevance',
    page: num('page') ?? 1,
    per_page: 24,
  }
  const { data, isPending, isError, isPlaceholderData } = useSearch(query)

  const toggle = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    const values = next.getAll(key)
    next.delete(key)
    for (const v of values.includes(value) ? values.filter((v) => v !== value) : [...values, value]) next.append(key, v)
    next.delete('page')
    setParams(next)
  }

  const set = (changes: Record<string, string | number | undefined>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value === undefined || value === '') next.delete(key)
      else next.set(key, String(value))
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  const categoryName = (slug: string) => categories?.find((c) => c.slug === slug)?.name ?? slug
  const selectedChips = FACETS.flatMap((f) => (query[f.key] ?? []).map((value) => ({ key: f.key, value })))
  const activePrice = Object.entries(PRICE_RANGES).find(([, r]) => r.min === query.min_price && r.max === query.max_price)?.[0]
  const pages = data ? Math.max(1, Math.ceil(data.total / data.per_page)) : 1

  return (
    <div className="grid gap-6 md:grid-cols-[210px_1fr]">
      <aside className="grid content-start gap-6 text-sm" aria-label="Filters">
        {data?.facets ? (
          <>
            {FACETS.map((facet) =>
              data.facets?.[facet.key]?.length ? (
                <fieldset key={facet.key} className="grid gap-1.5">
                  <legend className="mb-1 text-xs font-bold tracking-widest text-muted uppercase">{facet.title}</legend>
                  {data.facets[facet.key].map((option) => {
                    const checked = (query[facet.key] ?? []).includes(option.value)
                    return (
                      <label key={option.value} className="flex cursor-pointer items-center justify-between gap-2">
                        <span className="flex items-center gap-2">
                          <input type="checkbox" checked={checked} onChange={() => toggle(facet.key, option.value)} className="size-4 accent-brand" />
                          {facet.key === 'color' ? (
                            <span className="size-3.5 rounded-full ring-1 ring-line" style={{ background: SWATCHES[option.value] ?? '#ccc' }} aria-hidden="true" />
                          ) : null}
                          <span className="capitalize">{facet.key === 'category' ? categoryName(option.value) : option.value}</span>
                        </span>
                        <span className="text-muted tabular">{option.count}</span>
                      </label>
                    )
                  })}
                </fieldset>
              ) : null,
            )}
            <fieldset className="grid gap-1.5">
              <legend className="mb-1 text-xs font-bold tracking-widest text-muted uppercase">Price</legend>
              {data.facets.price?.map((bucket) => {
                const range = PRICE_RANGES[bucket.value]
                if (!range) return null
                return (
                  <label key={bucket.value} className="flex cursor-pointer items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="price"
                        checked={activePrice === bucket.value}
                        onChange={() => set({ min_price: range.min, max_price: range.max })}
                        className="size-4 accent-brand"
                      />
                      {range.label}
                    </span>
                    <span className="text-muted tabular">{bucket.count}</span>
                  </label>
                )
              })}
              {activePrice ? (
                <button type="button" onClick={() => set({ min_price: undefined, max_price: undefined })} className="text-left font-semibold text-brand">
                  Any price
                </button>
              ) : null}
            </fieldset>
          </>
        ) : data ? (
          <p className="rounded-lg bg-warn-soft p-3 text-warn">Filters are limited right now. Results still match your search.</p>
        ) : null}
        <label className="flex items-center gap-2 font-semibold">
          <input type="checkbox" checked={query.in_stock} onChange={(e) => set({ in_stock: e.target.checked ? 'true' : undefined })} className="size-4 accent-brand" />
          In stock only
        </label>
      </aside>

      <section className="grid content-start gap-4" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-extrabold">{query.q ? `Results for “${query.q}”` : 'All products'}</h1>
          <div className="flex items-center gap-3 text-sm">
            {data ? <span className="text-muted tabular">{data.total.toLocaleString('en-IN')} results</span> : null}
            <label className="sr-only" htmlFor="search-sort">Sort by</label>
            <select id="search-sort" value={query.sort} onChange={(e) => set({ sort: e.target.value })} className="rounded-lg border border-line bg-surface px-3 py-2">
              {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>

        {selectedChips.length ? (
          <div className="flex flex-wrap gap-2">
            {selectedChips.map((chip) => (
              <button key={`${chip.key}-${chip.value}`} type="button" onClick={() => toggle(chip.key, chip.value)} className="rounded-full border border-line bg-surface px-3 py-1 text-sm capitalize hover:border-brand">
                {chip.key === 'category' ? categoryName(chip.value) : chip.value} <span aria-hidden="true">✕</span>
                <span className="sr-only">Remove filter</span>
              </button>
            ))}
          </div>
        ) : null}

        {isError ? (
          <p className="rounded-lg bg-crit-soft p-4 text-crit">Search isn't working right now. Please try again.</p>
        ) : isPending ? (
          <p className="text-muted">Searching…</p>
        ) : data.items.length === 0 ? (
          <p className="rounded-lg bg-surface p-6 text-muted">No products match. Check the spelling or remove a filter.</p>
        ) : (
          <div className={`grid grid-cols-2 gap-4 lg:grid-cols-3 ${isPlaceholderData ? 'opacity-60' : ''}`}>
            {data.items.map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        )}

        {data && pages > 1 ? (
          <nav className="flex items-center justify-center gap-3 pt-2 text-sm" aria-label="Pages">
            <button type="button" disabled={query.page === 1} onClick={() => set({ page: (query.page ?? 1) - 1 })} className="rounded-lg border border-line bg-surface px-3 py-2 disabled:opacity-40">Previous</button>
            <span className="text-muted tabular">Page {query.page} of {pages}</span>
            <button type="button" disabled={query.page === pages} onClick={() => set({ page: (query.page ?? 1) + 1 })} className="rounded-lg border border-line bg-surface px-3 py-2 disabled:opacity-40">Next</button>
          </nav>
        ) : null}
      </section>
    </div>
  )
}
