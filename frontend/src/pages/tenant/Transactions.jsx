import { useEffect, useState } from 'react'
import { api, formatMoney, listItems } from '../../api/client'

export default function TenantTransactions() {
  const [rows, setRows] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.payments({ page: 1, page_size: 100 }).then((res) => setRows(listItems(res))).catch((e) => setError(e.message))
  }, [])

  async function openDetail(id) {
    setSelected(id)
    setDetail(null)
    try {
      setDetail(await api.payment(id))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Transactions</h2>
          <p className="muted">Drill from summary → fees → timeline. Geography shown is the immutable payment snapshot.</p>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Amount</th>
              <th>Fee</th>
              <th>Status</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => openDetail(t.transaction_id)}>
                <td><strong>{t.transaction_reference}</strong></td>
                <td>{formatMoney(t.amount)}</td>
                <td>{formatMoney(t.service_fee)}</td>
                <td><span className="pill">{t.status}</span></td>
                <td>{new Date(t.initiated_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && detail && (
        <div className="panel stack" style={{ marginTop: '1rem' }}>
          <div className="app-top">
            <h3>{detail.transaction_reference}</h3>
            <span className="pill">{detail.status}</span>
          </div>
          <div className="stat-grid">
            <div className="stat"><span className="muted">Amount</span><strong>{formatMoney(detail.amount)}</strong></div>
            <div className="stat"><span className="muted">Service fee</span><strong>{formatMoney(detail.service_fee)}</strong></div>
            <div className="stat"><span className="muted">Commission</span><strong>{formatMoney(detail.commission_amount)}</strong></div>
            <div className="stat"><span className="muted">Total</span><strong>{formatMoney(detail.total_amount)}</strong></div>
          </div>
          <p className="muted">Payer · Channel · Snapshot geography are system-resolved — tenant IDs are not edited in the UI.</p>
          <div><span className="muted">Payment channel</span><br /><strong>{detail.payment_channel}</strong></div>
          <div><span className="muted">Zone snapshot</span><br /><strong>{detail.transaction_geographic_unit_id}</strong></div>
          {detail.receipt_number && <div><span className="muted">Receipt</span><br /><strong>{detail.receipt_number}</strong></div>}

          <details className="details-block" open>
            <summary>State history</summary>
            <div className="timeline" style={{ marginTop: '0.75rem' }}>
              {(detail.events || []).map((e, i) => (
                <div className="item" key={i}>
                  <strong>{e.to_status}</strong>
                  <span className="muted">{e.note} · {new Date(e.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </details>
          <details className="details-block">
            <summary>Fee / commission breakdown</summary>
            <p style={{ marginTop: '0.75rem' }}>
              Gross {formatMoney(detail.amount)} − commission {formatMoney(detail.commission_amount)} = net to council{' '}
              {formatMoney(Number(detail.amount) - Number(detail.commission_amount))}.
              Service fee {formatMoney(detail.service_fee)} is platform revenue.
            </p>
          </details>
        </div>
      )}
    </div>
  )
}
