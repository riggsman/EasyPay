import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function TenantSettlements() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function load() {
    setRows(await api.settlements())
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function calculate() {
    setError('')
    setMessage('')
    try {
      const end = new Date()
      const start = new Date()
      start.setDate(end.getDate() - 30)
      await api.calculateSettlement({
        period_start: start.toISOString(),
        period_end: end.toISOString(),
      })
      setMessage('Settlement calculated')
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function approve(id) {
    try {
      await api.approveSettlement(id)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="rise">
      <div className="app-top">
        <h2>Settlements</h2>
        <button className="btn btn-primary" type="button" onClick={calculate}>Calculate (last 30 days)</button>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Gross</th><th>Fees</th><th>Commission</th><th>Net</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.settlement_id}>
                <td>{s.settlement_reference}</td>
                <td>{formatMoney(s.gross_amount)}</td>
                <td>{formatMoney(s.service_fees)}</td>
                <td>{formatMoney(s.commission_amount)}</td>
                <td>{formatMoney(s.net_amount)}</td>
                <td><span className="pill">{s.status}</span></td>
                <td>
                  {s.status === 'PENDING_APPROVAL' && (
                    <button className="btn btn-ghost" type="button" onClick={() => approve(s.settlement_id)}>Approve</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
