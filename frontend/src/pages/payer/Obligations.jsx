import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'

export default function ObligationsPage() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.obligations({ page: 1, page_size: 100 }).then((res) => setRows(listItems(res))).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="rise">
      <div className="app-top">
        <h2>My Obligations</h2>
        <Link className="btn btn-primary" to="/payer/pay/council">Pay council levy</Link>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
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
            {rows.map((o) => (
              <tr key={o.obligation_id}>
                <td>{o.description}</td>
                <td>{formatMoney(o.amount, o.currency)}</td>
                <td>{formatMoney(o.balance, o.currency)}</td>
                <td><span className="pill">{o.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
