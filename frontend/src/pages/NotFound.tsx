import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="rounded-xl bg-surface p-8 text-center">
      <h1 className="text-2xl font-extrabold">Page not found</h1>
      <Link to="/" className="mt-3 inline-block font-semibold text-brand">Back to the shop</Link>
    </div>
  )
}
