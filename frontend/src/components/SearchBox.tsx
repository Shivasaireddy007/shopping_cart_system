import { useNavigate, useSearchParams } from 'react-router-dom'

export function SearchBox() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const current = params.get('q') ?? ''

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault()
        const q = String(new FormData(e.currentTarget).get('q') ?? '').trim()
        navigate(q ? `/search?q=${encodeURIComponent(q)}` : '/search')
      }}
      className="order-last w-full sm:order-none sm:w-auto sm:flex-1"
    >
      <label htmlFor="site-search" className="sr-only">Search products</label>
      {/* Keyed on the URL's query so the box resets when you navigate. */}
      <input
        key={current}
        id="site-search"
        name="q"
        type="search"
        defaultValue={current}
        placeholder="Search shoes, shirts, brands…"
        className="w-full rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm"
      />
    </form>
  )
}
