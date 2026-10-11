import { NavLink, Outlet } from 'react-router-dom'

const TABS = [
  { to: '/admin', label: 'Products', end: true },
  { to: '/admin/orders', label: 'Orders', end: false },
  { to: '/admin/shipments', label: 'Shipments', end: false },
]

export function AdminLayout() {
  return (
    <div className="grid gap-5">
      <nav className="flex gap-1 border-b border-line" aria-label="Admin sections">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `-mb-px border-b-2 px-4 py-2 text-sm font-semibold ${isActive ? 'border-brand text-brand' : 'border-transparent text-muted hover:text-ink'}`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
