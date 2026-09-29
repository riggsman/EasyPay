import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'
import { Disclosure, EmptyRow, PageHeader, StatLink } from '../../components/OpsUI'

export default function PayerStatements() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.opsPayerStatement().then(setData).catch((e) => setError(e.message))
  }, [])
  return (
    <div className="rise stack">
      <PageHeader title="My Statements" subtitle="Settled payments with historical zone snapshots." />
      {error && <div className="alert">{error}</div>}
      <div className="stat-grid">
        <StatLink label="Paid total" value={formatMoney(data?.paid_total)} />
        <StatLink label="Fees paid" value={formatMoney(data?.fees_total)} />
      </div>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Date</th><th>Amount</th><th>Fee</th><th>Total</th><th>Receipt</th></tr></thead>
          <tbody>
            {(data?.lines || []).map((l, i) => (
              <tr key={i}>
                <td>{l.reference}</td>
                <td>{l.date ? new Date(l.date).toLocaleDateString() : '—'}</td>
                <td>{formatMoney(l.amount)}</td>
                <td>{formatMoney(l.fee)}</td>
                <td>{formatMoney(l.total)}</td>
                <td>{l.receipt_number || '—'}</td>
              </tr>
            ))}
            {!data?.lines?.length && <EmptyRow cols={6} />}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function PayerNotifications() {
  const [payments, setPayments] = useState([])
  const [area, setArea] = useState(null)
  useEffect(() => {
    Promise.all([api.payments(), api.operatingArea()])
      .then(([p, a]) => {
        setPayments(p.slice(0, 10))
        setArea(a)
      })
      .catch(() => {})
  }, [])
  const notices = []
  if (area?.history?.some((h) => !h.effective_to && h.change_source !== 'REGISTRATION' && h.change_source !== 'SEED')) {
    notices.push({ title: 'Operating area active', body: 'Your current operating zone is in effect for new payments only.' })
  }
  payments.filter((p) => p.status === 'SETTLED').slice(0, 5).forEach((p) => {
    notices.push({
      title: `Payment settled · ${p.transaction_reference}`,
      body: `Total ${formatMoney(p.total_amount)}. Historical zone snapshot retained.`,
      to: `/payer/payments/${p.transaction_id}`,
    })
  })
  payments.filter((p) => ['INITIATED', 'PROCESSING'].includes(p.status)).forEach((p) => {
    notices.push({
      title: `Payment in progress · ${p.transaction_reference}`,
      body: `Status ${p.status}`,
      to: `/payer/payments/${p.transaction_id}`,
    })
  })

  return (
    <div className="rise stack">
      <PageHeader title="Notifications" subtitle="Payment and zone activity for your account." />
      <div className="stack">
        {notices.map((n, i) => (
          <div className="panel" key={i}>
            <strong>{n.title}</strong>
            <p className="muted">{n.body}</p>
            {n.to && <Link to={n.to}>View</Link>}
          </div>
        ))}
        {!notices.length && <div className="panel muted">No notifications yet.</div>}
      </div>
      <Disclosure title="About notifications">
        <p>These are derived from your payment and operating-area history. External email/SMS providers can be wired in Phase 10.</p>
      </Disclosure>
    </div>
  )
}
