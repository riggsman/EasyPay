import { NavLink, Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useRealtime } from '../contexts/RealtimeContext'
import { api } from '../api/client'

const DROPDOWN_NAV_LABELS = new Set([
  'Platform / Tenant',
  'Configuration',
  'Operations',
  'Finance',
  'Governance',
])

function pathMatchesItem(pathname, item) {
  if (item.end) return pathname === item.to
  return pathname === item.to || pathname.startsWith(`${item.to}/`)
}

function groupContainsPath(group, pathname) {
  return group.items.some((item) => pathMatchesItem(pathname, item))
}

export function PublicLayout() {
  const { isAuthenticated, userType, logout } = useAuth()
  const location = useLocation()
  const isLanding = location.pathname === '/'
  // Login / password-reset: brand only — no public nav or footer chrome.
  const isAuthFocus =
    location.pathname === '/login' || location.pathname === '/forgot-password'

  const shellClass = isLanding
    ? 'public-shell public-shell--landing'
    : isAuthFocus
      ? 'public-shell public-shell--auth'
      : 'public-shell'

  return (
    <div className={shellClass}>
      {isAuthFocus ? (
        <div className="auth-stack rise">
          <Link to="/" className="brand auth-stack-brand">EasyPay</Link>
          <Outlet />
        </div>
      ) : (
        <>
          <header className={`public-nav rise${isLanding ? ' public-nav--overlay' : ''}`}>
            <div className="container public-nav-inner">
              <Link to="/" className="brand">EasyPay</Link>
              <nav className="nav-links">
                <Link to="/#how">How it works</Link>
                <Link to="/verify">Verify</Link>
                {isAuthenticated ? (
                  <>
                    <Link to={userType === 'PAYER' ? '/payer' : (userType === 'PLATFORM_ADMIN' || userType === 'SUPER_ADMIN') ? '/platform' : '/tenant'}>
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
            </div>
          </header>
          <Outlet />
          <div className="container footer">
            <span>© {new Date().getFullYear()} EasyPay Collection Platform</span>
            <span>About · Support · Verification · Terms · Privacy</span>
          </div>
        </>
      )}
    </div>
  )
}

function OpsShell({ title, links, contextLabel, basePath, showOpsChrome = true, tenantOptions = [] }) {
  const { logout, session } = useAuth()
  const realtime = useRealtime()
  const navigate = useNavigate()
  const location = useLocation()
  const [alerts, setAlerts] = useState(null)
  const [q, setQ] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [tenantFilter, setTenantFilter] = useState(localStorage.getItem('ep_tenant_filter') || '')
  const [openGroups, setOpenGroups] = useState(() => {
    const initial = {}
    for (const group of links) {
      if (!(group.dropdown || DROPDOWN_NAV_LABELS.has(group.label))) continue
      if (groupContainsPath(group, window.location.pathname)) initial[group.label] = true
    }
    return initial
  })

  useEffect(() => {
    setOpenGroups((prev) => {
      const next = { ...prev }
      for (const group of links) {
        if (!(group.dropdown || DROPDOWN_NAV_LABELS.has(group.label))) continue
        if (groupContainsPath(group, location.pathname)) next[group.label] = true
      }
      return next
    })
  }, [location.pathname, links])

  useEffect(() => {
    if (!showOpsChrome) return
    api.opsAlerts().then(setAlerts).catch(() => {})
  }, [showOpsChrome])

  useEffect(() => {
    if (!showOpsChrome) return undefined
    function onRealtime(e) {
      const msg = e.detail
      if (msg?.type === 'alerts.updated') {
        if (session?.user_type === 'STAFF' && msg.tenant_id && msg.tenant_id !== session?.tenant_id) return
        if (session?.user_type === 'PLATFORM_ADMIN' && tenantFilter && msg.tenant_id && msg.tenant_id !== tenantFilter) return
        const { digest: _d, ...snapshot } = msg.payload || {}
        setAlerts(snapshot)
      }
    }
    window.addEventListener('ep:realtime', onRealtime)
    return () => window.removeEventListener('ep:realtime', onRealtime)
  }, [showOpsChrome, session?.user_type, session?.tenant_id, tenantFilter])

  useEffect(() => {
    if (tenantFilter) localStorage.setItem('ep_tenant_filter', tenantFilter)
    else localStorage.removeItem('ep_tenant_filter')
    window.dispatchEvent(new CustomEvent('ep:tenant-filter', { detail: tenantFilter || null }))
  }, [tenantFilter])

  useEffect(() => {
    if (!showOpsChrome) return
    const term = q.trim()
    if (term.length < 2) {
      setSearchResults(null)
      return undefined
    }
    const handle = setTimeout(() => {
      api.opsSearch(term, tenantFilter || undefined)
        .then(setSearchResults)
        .catch(() => setSearchResults({ query: term, results: [] }))
    }, 300)
    return () => clearTimeout(handle)
  }, [q, tenantFilter, showOpsChrome])

  const alertCount = alerts
    ? (alerts.pending_transactions || 0) + (alerts.rejected_transactions || 0) + (alerts.settlements_awaiting_approval || 0)
    : 0

  function onSearchKey(e) {
    if (e.key === 'Enter' && q.trim().length >= 2) {
      navigate(`${basePath}/search`)
    }
  }

  return (
    <div className="ops-shell">
      <header className="ops-topbar">
        <div className="ops-top-left">
          <Link to="/" className="brand">EasyPay</Link>
          <span className="ops-context">{contextLabel || title}</span>
          {showOpsChrome && tenantOptions.length > 0 && (
            <select
              className="ops-tenant-select"
              aria-label="Tenant selector"
              value={tenantFilter}
              onChange={(e) => setTenantFilter(e.target.value)}
            >
              <option value="">All tenants</option>
              {tenantOptions.map((t) => (
                <option key={t.tenant_id} value={t.tenant_id}>{t.organization_name}</option>
              ))}
            </select>
          )}
        </div>
        <div className="ops-top-right">
          <input
            className="ops-search"
            type="search"
            placeholder="Search reference, payer, receipt…"
            aria-label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onSearchKey}
          />
          {showOpsChrome && (
            <Link to={`${basePath}/alerts`} className="ops-alert-chip" title="Operational alerts">
              Alerts{alertCount ? ` · ${alertCount}` : ''}
            </Link>
          )}
          {showOpsChrome && (
            <span className="muted" title={realtime?.connected ? 'Realtime connected' : 'Realtime offline'}>
              <span className={`ops-live-dot ${realtime?.connected ? 'on' : ''}`} />
              Live
            </span>
          )}
          <span className="ops-user">{session?.full_name}</span>
          <button className="btn btn-ghost" type="button" onClick={logout}>Sign out</button>
        </div>
      </header>
      <div className="ops-body">
        <aside className="ops-aside">
          <p className="ops-aside-title">{title}</p>
          <nav>
            {links.map((group) => {
              const isDropdown = group.dropdown || DROPDOWN_NAV_LABELS.has(group.label)
              const isOpen = !isDropdown || openGroups[group.label] === true
              const activeInGroup = groupContainsPath(group, location.pathname)
              return (
                <div
                  key={group.label}
                  className={`ops-nav-group${isDropdown ? ' ops-nav-dropdown' : ''}${isOpen ? ' is-open' : ''}${activeInGroup ? ' has-active' : ''}`}
                >
                  {isDropdown ? (
                    <button
                      type="button"
                      className="ops-nav-label ops-nav-toggle"
                      aria-expanded={isOpen}
                      onClick={() =>
                        setOpenGroups((prev) => ({
                          ...prev,
                          [group.label]: !prev[group.label],
                        }))
                      }
                    >
                      <span>{group.label}</span>
                      <span className="ops-nav-chevron" aria-hidden="true" />
                    </button>
                  ) : (
                    <div className="ops-nav-label">{group.label}</div>
                  )}
                  {isOpen && (
                    <div className="ops-nav-items">
                      {group.items.map((l) => (
                        <NavLink key={l.to} to={l.to} end={l.end}>{l.label}</NavLink>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </nav>
        </aside>
        <main className="ops-main">
          <Outlet context={{ searchQuery: q, tenantFilter, basePath, searchResults }} />
        </main>
      </div>
    </div>
  )
}

function tenantLinks(base = '/tenant') {
  return [
    {
      label: 'Overview',
      items: [
        { to: base, label: 'Dashboard', end: true },
        { to: `${base}/alerts`, label: 'Alerts' },
        { to: `${base}/search`, label: 'Search' },
      ],
    },
    {
      label: 'Identity & Access',
      items: [{ to: `${base}/users`, label: 'Users & Roles' }],
    },
    {
      label: 'Configuration',
      dropdown: true,
      items: [
        { to: `${base}/revenue`, label: 'Revenue Types' },
        { to: `${base}/fees`, label: 'Fees' },
        { to: `${base}/commissions`, label: 'Commissions' },
        { to: `${base}/config`, label: 'System Config' },
      ],
    },
    {
      label: 'Operations',
      dropdown: true,
      items: [
        { to: `${base}/payers`, label: 'Payers' },
        { to: `${base}/obligations`, label: 'Obligations' },
        { to: `${base}/collections`, label: 'Collections' },
        { to: `${base}/transactions`, label: 'Transactions' },
      ],
    },
    {
      label: 'Finance',
      dropdown: true,
      items: [
        { to: `${base}/ledger`, label: 'Ledger' },
        { to: `${base}/receipts`, label: 'Receipts' },
        { to: `${base}/settlements`, label: 'Settlements' },
        { to: `${base}/reconciliation`, label: 'Reconciliation' },
        { to: `${base}/statements`, label: 'Statements' },
        { to: `${base}/reports`, label: 'Reports' },
      ],
    },
    {
      label: 'Governance',
      dropdown: true,
      items: [{ to: `${base}/audit`, label: 'Audit Trail' }],
    },
  ]
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
        { to: '/payer/statements', label: 'Statements' },
        { to: '/payer/notifications', label: 'Notifications' },
        { to: '/payer/area', label: 'Operating Area' },
        { to: '/payer/profile', label: 'Profile' },
      ],
    },
  ]
  return <OpsShell title="Payer Portal" links={links} contextLabel="Payer session" basePath="/payer" showOpsChrome={false} />
}

export function TenantLayout() {
  return (
    <OpsShell
      title="Council Console"
      links={tenantLinks('/tenant')}
      contextLabel="Tenant context locked"
      basePath="/tenant"
      showOpsChrome
    />
  )
}

export function PlatformLayout() {
  const [tenants, setTenants] = useState([])
  useEffect(() => {
    api.tenants().then(setTenants).catch(() => {})
  }, [])
  const links = [
    {
      label: 'Overview',
      items: [
        { to: '/platform', label: 'Dashboard', end: true },
        { to: '/platform/alerts', label: 'Alerts' },
        { to: '/platform/search', label: 'Search' },
      ],
    },
    {
      label: 'Platform / Tenant',
      dropdown: true,
      items: [
        { to: '/platform/tenants', label: 'Tenants' },
        { to: '/platform/geography', label: 'Geography' },
        { to: '/platform/users', label: 'Users & Roles' },
      ],
    },
    {
      label: 'Configuration',
      dropdown: true,
      items: [
        { to: '/platform/providers', label: 'Providers (Campay / Email / WA / SMS)' },
        { to: '/platform/fees', label: 'Fees' },
        { to: '/platform/commissions', label: 'Commissions' },
        { to: '/platform/config', label: 'System Config' },
      ],
    },
    {
      label: 'Operations',
      dropdown: true,
      items: [
        { to: '/platform/payers', label: 'Payers' },
        { to: '/platform/obligations', label: 'Obligations' },
        { to: '/platform/collections', label: 'Collections' },
        { to: '/platform/transactions', label: 'Transactions' },
      ],
    },
    {
      label: 'Finance',
      dropdown: true,
      items: [
        { to: '/platform/ledger', label: 'Ledger' },
        { to: '/platform/receipts', label: 'Receipts' },
        { to: '/platform/settlements', label: 'Settlements' },
        { to: '/platform/reconciliation', label: 'Reconciliation' },
        { to: '/platform/statements', label: 'Statements' },
        { to: '/platform/reports', label: 'Reports' },
      ],
    },
    {
      label: 'Governance',
      dropdown: true,
      items: [{ to: '/platform/audit', label: 'Audit Trail' }],
    },
  ]
  return (
    <OpsShell
      title="Platform Console"
      links={links}
      contextLabel="Platform scope"
      basePath="/platform"
      showOpsChrome
      tenantOptions={tenants}
    />
  )
}
