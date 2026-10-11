import { Navigate, Outlet } from 'react-router-dom'

import { useMe } from '../../hooks/queries'
import { useAuth } from '../../stores/auth'

export function RequireAdmin() {
  const signedIn = useAuth((s) => s.accessToken !== null)
  const { data: me, isPending } = useMe()

  if (!signedIn) return <Navigate to="/login" state={{ from: '/admin' }} replace />
  if (isPending) return <p className="text-muted">Checking access…</p>
  if (!me?.is_admin) return <p className="rounded-lg bg-surface p-6">This area is for shop admins.</p>
  return <Outlet />
}
