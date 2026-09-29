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

function OpsShell({ title, links, contextLabel }) {
  const { logout, session } = useAuth()
  return (
    <div className="ops-shell">
      <header className="ops-topbar">
        <div className="ops-top-left">
          <Link to="/" className="brand">EasyPay</Link>
          <span className="ops-context">{contextLabel || title}</span>
        </div>
        <div className="ops-top-right">
          <input className="ops-search" type="search" placeholder="Search reference, payer, receipt…" aria-label="Search" />
          <span className="ops-user">{session?.full_name}</span>
          <button className="btn btn-ghost" type="button" onClick={logout}>Sign out</button>
        </div>
      </header>
      <div className="ops-body">
        <aside className="ops-aside">
          <p className="ops-aside-title">{title}</p>
          <nav>
            {links.map((group) => (
              <div key={group.label} className="ops-nav-group">
                <div className="ops-nav-label">{group.label}</div>
                {group.items.map((l) => (
                  <NavLink key={l.to} to={l.to} end={l.end}>{l.label}</NavLink>
                ))}
              </div>
            ))}
          </nav>
        </aside>
        <main className="ops-main"><Outlet /></main>
      </div>
    </div>
  )
}

export function PayerLayout() {
  const links = [
    {
      label: 'Portal',
      items: [
        { to: '/payer', label: 'Dashboard', end: true },
        { to: '/payer/obligations', label: 'Obligations' },
        { to: '/payer/pay', label: 'Make Payment' },
        { to: '/payer/history', label: 'Transactions' },
        { to: '/payer/receipts', label: 'Receipts' },
        { to: '/payer/area', label: 'Operating Area' },
        { to: '/payer/profile', label: 'Profile' },
      ],
    },
  ]
  return <OpsShell title="Payer Portal" links={links} contextLabel="Payer session" />
}

export function TenantLayout() {
  const { session } = useAuth()
  const links = [
    {
      label: 'Operations',
      items: [
        { to: '/tenant', label: 'Dashboard', end: true },
        { to: '/tenant/obligations', label: 'Obligations' },
        { to: '/tenant/transactions', label: 'Transactions' },
      ],
    },
    {
      label: 'Configuration',
      items: [
        { to: '/tenant/revenue', label: 'Revenue Setup' },
      ],
    },
    {
      label: 'Finance',
      items: [
        { to: '/tenant/settlements', label: 'Settlements' },
        { to: '/tenant/reports', label: 'Reports' },
      ],
    },
  ]
  return (
    <OpsShell
      title="Council Console"
      links={links}
      contextLabel={session?.tenant_id ? 'Tenant context locked' : 'Council Admin'}
    />
  )
}

export function PlatformLayout() {
  const links = [
    {
      label: 'Platform',
      items: [
        { to: '/platform', label: 'Dashboard', end: true },
        { to: '/platform/tenants', label: 'Tenants' },
        { to: '/platform/geography', label: 'Geography' },
      ],
    },
    {
      label: 'Finance',
      items: [{ to: '/platform/reports', label: 'Reports' }],
    },
  ]
  return <OpsShell title="Platform Console" links={links} contextLabel="All tenants" />
}
