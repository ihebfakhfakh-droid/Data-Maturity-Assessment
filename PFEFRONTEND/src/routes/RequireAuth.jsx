import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider.jsx'

export function RequireAuth() {
  const auth = useAuth()
  const location = useLocation()

  if (auth.ready === false) {
    return null
  }

  if (!auth.isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

