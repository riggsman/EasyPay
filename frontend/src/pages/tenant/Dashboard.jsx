import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function TenantDashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.tenantDashboard().then(setStats).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="rise">
      <h2>Council Dashboard</h2>
      {error && <div className="alert">{error}</div>}
      <div className="stat-grid">
        <div className="panel stat"><span className="muted">Collections today</span><strong>{formatMoney(stats?.collections_today)}</strong></div>
        <div className="panel stat"><span className="muted">Transactions</span><strong>{stats?.transactions_today ?? 0}</strong></div>
        <div className="panel stat"><span className="muted">Successful</span><strong>{stats?.successful_today ?? 0}</strong></div>
        <div className="panel stat"><span className="muted">Pending</span><strong>{stats?.pending_today ?? 0}</strong></div>
        <div className="panel stat"><span className="muted">Rejected</span><strong>{stats?.rejected_today ?? 0}</strong></div>
      </div>
    </div>
  )
}
