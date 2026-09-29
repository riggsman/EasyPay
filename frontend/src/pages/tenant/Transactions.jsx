import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function TenantTransactions() {
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.payments().then(setRows).catch(() => {})
  }, [])
  return (
    <div className="rise">
      <h2>Transactions</h2>
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Amount</th><th>Fee</th><th>Status</th><th>Zone snapshot</th></tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.transaction_id}>
                <td>{t.transaction_reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td>{formatMoney(t.service_fee)}</td>
                <td><span className="pill">{t.status}</span></td>
                <td className="muted">{t.transaction_geographic_unit_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
