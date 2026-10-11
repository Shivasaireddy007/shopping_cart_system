import { useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useCart, useMe } from '../hooks/queries'
import { useAuth } from '../stores/auth'
import { Logo } from './Logo'

export function Layout() {
  const { data: me } = useMe()
  const { data: cart } = useCart()
  const logout = useAuth((s) => s.logout)
  const client = useQueryClient()
  const navigate = useNavigate()
  const count = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0

  const signOut = () => {
    logout()
    client.clear()
    navigate('/')
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `font-semibold ${isActive ? 'text-brand' : 'text-muted hover:text-ink'}`

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link to="/" aria-label="Shopping Cart home">
            <Logo />
          </Link>
          <nav className="ml-auto flex items-center gap-5 text-sm">
            {me?.is_admin ? (
              <NavLink to="/admin" className={linkClass}>
                Admin
              </NavLink>
            ) : null}
            <NavLink to="/cart" className={linkClass}>
              Cart
              {count > 0 ? (
                <span className="ml-1 rounded-full bg-accent px-1.5 py-0.5 text-xs text-white tabular">{count}</span>
              ) : null}
            </NavLink>
            {me ? (
              <button type="button" onClick={signOut} className="font-semibold text-muted hover:text-ink">
                Sign out
              </button>
            ) : (
              <NavLink to="/login" className={linkClass}>
                Sign in
              </NavLink>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
