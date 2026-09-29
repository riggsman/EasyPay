import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'

export default function PaymentDetail() {
  const { id } = useParams()
  const [txn, setTxn] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.payment(id).then(setTxn).catch((e) => setError(e.message))
  }, [id])

  if (error) return <div className="alert">{error}</div>
  if (!txn) return <p>Loading…</p>

  return (
    <div className="rise stack">
      <div className="app-top">
        <div>
          <h2>{txn.transaction_reference}</h2>
          <span className="pill">{txn.status}</span>
        </div>
        {txn.receipt_id && <Link className="btn btn-primary" to={`/payer/receipts`}>View Receipts</Link>}
      </div>
      <div className="panel stack">
        <div><strong>{formatMoney(txn.total_amount, txn.currency)}</strong> total (incl. {formatMoney(txn.service_fee, txn.currency)} fee)</div>
        {txn.receipt_number && <div>Receipt: {txn.receipt_number}</div>}
        <h3>Transaction timeline</h3>
        <div className="timeline">
          {(txn.events || []).map((e, i) => (
            <div className="item" key={i}>
              <strong>{e.to_status}</strong>
              <span className="muted">{e.note} · {new Date(e.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
        {txn.receipt_number && (
          <Link to="/verify">Verify Receipt</Link>
        )}
      </div>
    </div>
  )
}
