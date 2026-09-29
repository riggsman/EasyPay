import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function PlatformDashboard() {
  const [stats, setStats] = useState(null)
  useEffect(() => {
    api.platformDashboard().then(setStats).catch(() => {})
  }, [])
  return (
    <div className="rise">
      <h2>Platform Dashboard</h2>
      <div className="stat-grid">
        <div className="panel stat"><span className="muted">Collections today</span><strong>{formatMoney(stats?.collections_today)}</strong></div>
        <div className="panel stat"><span className="muted">Transactions today</span><strong>{stats?.transactions_today ?? 0}</strong></div>
      </div>
    </div>
  )
}
