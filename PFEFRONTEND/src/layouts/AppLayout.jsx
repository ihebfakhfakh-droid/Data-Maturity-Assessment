import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider.jsx'
import { homePathForRole } from '../auth/roles.js'

export function AppLayout() {
  const auth = useAuth()
  const location = useLocation()
  const role = String(auth.role ?? '').toUpperCase()
  const isLoginPage = location.pathname === '/login'

  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbarInner">
          <div className="brand">
            <NavLink
              to={auth.isAuthenticated ? homePathForRole(role) : '/login'}
              className="brandLink"
              aria-label="Devoteam home"
            >
              <img src="/devoteam-logo.png" alt="Devoteam" className="devoteamLogo" />
            </NavLink>
          </div>

          {auth.isAuthenticated ? (
            <div className="topbarRight">
              <div className="userPill">
                <span className="userEmail">{auth.subject ?? 'connected'}</span>
                {role ? <span className="roleBadge">{role}</span> : null}
              </div>
              <button type="button" className="btn btnPrimary btnSm" onClick={auth.logout}>
                Logout
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <main className={isLoginPage ? 'main mainLogin' : 'main'}>
        <Outlet />
      </main>
    </div>
  )
}

