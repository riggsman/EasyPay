import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'

export default function PaymentHistory() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.payments().then(setRows).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="rise">
      <h2>Payment History</h2>
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Amount</th>
              <th>Total</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.transaction_id}>
                <td>{t.transaction_reference}</td>
                <td>{formatMoney(t.amount, t.currency)}</td>
                <td>{formatMoney(t.total_amount, t.currency)}</td>
                <td><span className="pill">{t.status}</span></td>
                <td><Link to={`/payer/payments/${t.transaction_id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
