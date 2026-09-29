import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'
import { Disclosure, EmptyRow, PageHeader, PaginationBar, StatLink } from '../../components/OpsUI'

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
      {data && (
        <div className="stat-grid">
          <StatLink label="Paid total" value={formatMoney(data.paid_total)} />
          <StatLink label="Fees total" value={formatMoney(data.fees_total)} />
        </div>
      )}
      <Disclosure title="Statement lines" open>
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
                <td className="muted">{l.receipt_number || '—'}</td>
              </tr>
            ))}
            {!data?.lines?.length && <EmptyRow cols={6} />}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function PayerNotifications() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .myNotifications({ page, page_size: pageSize })
      .then((res) => {
        setRows(listItems(res))
        setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
      })
      .catch((e) => setError(e.message))
  }, [page, pageSize])

  useEffect(() => {
    function onRealtime(e) {
      const msg = e.detail
      if (msg?.type === 'notification.delivery') {
        api.myNotifications({ page: 1, page_size: pageSize }).then((res) => {
          setPage(1)
          setRows(listItems(res))
          setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
        }).catch(() => {})
      }
    }
    window.addEventListener('ep:realtime', onRealtime)
    return () => window.removeEventListener('ep:realtime', onRealtime)
  }, [pageSize])

  return (
    <div className="rise stack">
      <PageHeader
        title="Notifications"
        subtitle="Outbound email / SMS / WhatsApp delivery records for your account."
      />
      {error && <div className="alert">{error}</div>}
      <div className="stack">
        {rows.map((n) => (
          <div className="panel" key={n.notification_id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>{n.channel} · {n.event_type}</strong>
              <span className="pill">{n.status}</span>
            </div>
            <p className="muted">{n.subject || n.body_preview || '—'}</p>
            <p className="muted">{n.created_at ? new Date(n.created_at).toLocaleString() : ''}</p>
            {n.entity_type === 'transaction' && n.entity_id && (
              <Link to={`/payer/payments/${n.entity_id}`}>View payment</Link>
            )}
          </div>
        ))}
        {!rows.length && <div className="panel muted">No notification deliveries yet. They appear after payment settlement or zone decisions when channels are enabled.</div>}
      </div>
      <PaginationBar
        page={page}
        totalPages={meta.total_pages}
        total={meta.total}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
      />
      <Disclosure title="About notifications">
        <p>
          These records come from the notification delivery log (email, SMS, WhatsApp). Channel enablement is controlled by platform configuration;
          SMS also requires the server master switch.
        </p>
      </Disclosure>
    </div>
  )
}
