import { NavLink, Outlet, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function PublicLayout() {
  const { isAuthenticated, userType, logout } = useAuth()
  return (
    <div>
      <div className="container">
        <header className="public-nav rise">
          <Link to="/" className="brand">EasyPay</Link>
          <nav className="nav-links">
            <Link to="/#how">How it works</Link>
            <Link to="/verify">Verify</Link>
            {isAuthenticated ? (
              <>
                <Link to={userType === 'PAYER' ? '/payer' : userType === 'PLATFORM_ADMIN' ? '/platform' : '/tenant'}>
                  Dashboard
                </Link>
                <button className="btn btn-ghost" type="button" onClick={logout}>Sign out</button>
              </>
            ) : (
              <>
                <Link to="/login">Sign In</Link>
                <Link className="btn btn-primary" to="/register">Create Account</Link>
              </>
            )}
          </nav>
        </header>
      </div>
      <Outlet />
      <div className="container footer">
        <span>© {new Date().getFullYear()} EasyPay Collection Platform</span>
        <span>About · Support · Verification · Terms · Privacy</span>
      </div>
    </div>
  )
}

function SideNav({ links, title }) {
  const { logout, session } = useAuth()
  return (
    <aside>
      <Link to="/" className="brand">EasyPay</Link>
      <p className="muted" style={{ color: 'rgba(255,255,255,0.7)', marginBottom: '1rem' }}>
        {title}<br />
        <small>{session?.full_name}</small>
      </p>
      <nav>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <button className="btn btn-ghost" style={{ marginTop: '1.5rem', color: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} type="button" onClick={logout}>
        Sign out
      </button>
    </aside>
  )
}

export function PayerLayout() {
  const links = [
    { to: '/payer', label: 'Dashboard', end: true },
    { to: '/payer/obligations', label: 'My Obligations' },
    { to: '/payer/pay', label: 'Make Payment' },
    { to: '/payer/history', label: 'Payment History' },
    { to: '/payer/receipts', label: 'Receipts' },
    { to: '/payer/area', label: 'Operating Area' },
    { to: '/payer/profile', label: 'My Profile' },
  ]
  return (
    <div className="app-shell">
      <SideNav links={links} title="Payer Portal" />
      <main className="app-main"><Outlet /></main>
    </div>
  )
}

export function TenantLayout() {
  const links = [
    { to: '/tenant', label: 'Dashboard', end: true },
    { to: '/tenant/obligations', label: 'Obligations' },
    { to: '/tenant/transactions', label: 'Transactions' },
    { to: '/tenant/settlements', label: 'Settlements' },
    { to: '/tenant/reports', label: 'Reports' },
  ]
  return (
    <div className="app-shell">
      <SideNav links={links} title="Council Admin" />
      <main className="app-main"><Outlet /></main>
    </div>
  )
}

export function PlatformLayout() {
  const links = [
    { to: '/platform', label: 'Dashboard', end: true },
    { to: '/platform/tenants', label: 'Tenants' },
    { to: '/platform/geography', label: 'Geography' },
    { to: '/platform/reports', label: 'Reports' },
  ]
  return (
    <div className="app-shell">
      <SideNav links={links} title="Platform Admin" />
      <main className="app-main"><Outlet /></main>
    </div>
  )
}
