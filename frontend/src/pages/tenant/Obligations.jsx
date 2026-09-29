import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function TenantObligations() {
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.obligations().then(setRows).catch(() => {})
  }, [])
  return (
    <div className="rise">
      <h2>Obligations</h2>
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Payer</th><th>Description</th><th>Amount</th><th>Balance</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.obligation_id}>
                <td className="muted">{o.payer_id}</td>
                <td>{o.description}</td>
                <td>{formatMoney(o.amount)}</td>
                <td>{formatMoney(o.balance)}</td>
                <td><span className="pill">{o.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
