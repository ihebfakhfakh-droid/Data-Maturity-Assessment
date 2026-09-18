import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider.jsx'
import { homePathForRole } from '../auth/roles.js'

export function RequireRole({ roles, children }) {
  const auth = useAuth()
  const wanted = (roles ?? []).map((r) => String(r).toUpperCase())
  const hasJwtRole = wanted.some((r) => auth.roles?.includes(r))
  const hasUserRole = wanted.includes(String(auth.role ?? '').toUpperCase())
  const allowed = hasJwtRole || hasUserRole

  if (!allowed) {
    if (!auth.isAuthenticated) return <Navigate to="/login" replace />
    // Authenticated but wrong role: send to their home.
    const r = String(auth.role ?? '').toUpperCase()
    return <Navigate to={homePathForRole(r)} replace />
  }
  return children
}

