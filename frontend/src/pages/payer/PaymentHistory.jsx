import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'

function todayInput() {
  return new Date().toISOString().slice(0, 10)
}

function monthStartInput() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

export default function PaymentHistory() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [quote, setQuote] = useState(null)
  const [dateFrom, setDateFrom] = useState(monthStartInput())
  const [dateTo, setDateTo] = useState(todayInput())
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)

  async function refreshQuote() {
    const q = await api.historyExportQuote()
    setQuote(q)
  }

  useEffect(() => {
    api.payments({ page: 1, page_size: 100 }).then((res) => setRows(listItems(res))).catch((e) => setError(e.message))
    api.mePayer().then((p) => setPhone(p.phone_number || '')).catch(() => {})
    refreshQuote().catch((e) => setError(e.message))
  }, [])

  async function onDownload(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)
    try {
      const result = await api.downloadHistoryExport(
        {
          date_from: `${dateFrom}T00:00:00`,
          date_to: `${dateTo}T23:59:59`,
          phone_number: quote?.will_charge ? phone : undefined,
        },
        `EasyPay-history-${dateFrom}_${dateTo}.pdf`,
      )
      await refreshQuote()
      setMessage(
        result.wasFree
          ? 'History downloaded using a free allowance.'
          : `History downloaded. Fee charged: ${formatMoney(result.feeAmount || quote?.fee_amount, quote?.currency || 'XAF')}.`,
      )
    } catch (err) {
      setError(err.message)
      refreshQuote().catch(() => {})
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rise stack">
      <h2>Payment History</h2>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}

      <form className="panel stack" onSubmit={onDownload}>
        <h3>Download transaction history</h3>
        {quote && (
          <p className="muted">
            Free downloads remaining: <strong>{quote.free_downloads_remaining}</strong> of {quote.free_downloads}.
            {quote.will_charge
              ? ` Next download is charged ${formatMoney(quote.fee_amount, quote.currency)} via Mobile Money.`
              : ' This download is free.'}
          </p>
        )}
        <div className="row" style={{ gap: '1rem', flexWrap: 'wrap' }}>
          <div className="field">
            <label>From</label>
            <input type="date" required value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div className="field">
            <label>To</label>
            <input type="date" required value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>
        {quote?.will_charge && (
          <div className="field" style={{ maxWidth: 320 }}>
            <label>MoMo phone for fee</label>
            <input
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="2376XXXXXXXX"
            />
          </div>
        )}
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? 'Generating…' : quote?.will_charge ? `Pay ${formatMoney(quote.fee_amount, quote.currency)} & download` : 'Download PDF'}
        </button>
      </form>

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
                <td>
                  {t.transaction_reference}
                  {t.product_type === 'UTILITY' ? <div className="muted" style={{ fontSize: '0.8rem' }}>Utility</div> : null}
                </td>
                <td>{formatMoney(t.amount, t.currency)}</td>
                <td>{formatMoney(t.total_amount, t.currency)}</td>
                <td>
                  <span className={`pill${t.status === 'FAILED' || t.status === 'REJECTED' ? ' failed' : ''}`}>
                    {t.status === 'REJECTED' ? 'FAILED' : t.status}
                  </span>
                </td>
                <td><Link to={`/payer/payments/${t.transaction_id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
