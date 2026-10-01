import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'

export default function PayerDashboard() {
  const [payer, setPayer] = useState(null)
  const [area, setArea] = useState(null)
  const [stats, setStats] = useState(null)
  const [obligations, setObligations] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.mePayer(), api.operatingArea(), api.payerDashboard(), api.obligations()])
      .then(([p, a, s, o]) => {
        setPayer(p)
        setArea(a)
        setStats(s)
        setObligations(listItems(o).slice(0, 5))
      })
      .catch((e) => setError(e.message))
  }, [])

  const leaf = area?.ancestry?.path?.slice(-1)?.[0]

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Good day, {payer?.business_name || payer?.full_name || '…'}</h2>
          <p className="muted">
            Operating Area: <strong>{leaf?.name || '—'}</strong>{' '}
            <Link to="/payer/area">Change Area</Link>
          </p>
        </div>
        <div className="row">
          <Link className="btn btn-ghost" to="/payer/services">Pay utility bill</Link>
          <Link className="btn btn-primary" to="/payer/pay">Make Payment</Link>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="stat-grid">
        <div className="panel stat">
          <span className="muted">Outstanding</span>
          <strong>{formatMoney(stats?.outstanding_obligations)}</strong>
        </div>
        <div className="panel stat">
          <span className="muted">Paid</span>
          <strong>{formatMoney(stats?.paid_total)}</strong>
        </div>
      </div>
      <div className="panel">
        <div className="app-top">
          <h3>Current Obligations</h3>
          <Link to="/payer/obligations">View All</Link>
        </div>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Description</th>
                <th>Amount</th>
                <th>Balance</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {obligations.map((o) => (
                <tr key={o.obligation_id}>
                  <td>{o.description}</td>
                  <td>{formatMoney(o.amount, o.currency)}</td>
                  <td>{formatMoney(o.balance, o.currency)}</td>
                  <td><span className="pill">{o.status}</span></td>
                </tr>
              ))}
              {!obligations.length && (
                <tr><td colSpan={4} className="muted">No obligations yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
