import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'

function newIdempotencyKey() {
  return `pay-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export default function CouncilPaymentPage() {
  const navigate = useNavigate()
  const [obligations, setObligations] = useState([])
  const [obligationId, setObligationId] = useState('')
  const [channel, setChannel] = useState('MOBILE_MONEY')
  const [phone, setPhone] = useState('')
  const [resolved, setResolved] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const due = useMemo(() => obligations.filter((o) => Number(o.balance) > 0), [obligations])

  useEffect(() => {
    api.obligations({ page: 1, page_size: 100 }).then((res) => {
      const rows = listItems(res)
      setObligations(rows)
      const first = rows.find((o) => Number(o.balance) > 0)
      if (first) setObligationId(first.obligation_id)
    }).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!obligationId) return
    setResolved(null)
    api.resolvePayment({ obligation_id: obligationId, payment_channel: channel })
      .then(setResolved)
      .catch((e) => setError(e.message))
  }, [obligationId, channel])

  async function confirm() {
    setLoading(true)
    setError('')
    try {
      const txn = await api.initiatePayment({
        obligation_id: obligationId,
        payment_channel: channel,
        phone_number: channel === 'MOBILE_MONEY' ? phone : undefined,
        idempotency_key: newIdempotencyKey(),
      })
      if (txn.status === 'REJECTED' || txn.status === 'FAILED') {
        throw new Error(txn.failure_reason || 'Mobile Money collection was rejected by Campay')
      }
      const detail = await api.confirmPayment(txn.transaction_id)
      navigate(`/payer/payments/${detail.transaction_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Council levies</h2>
          <p className="muted">Pay obligations for your current operating council.</p>
        </div>
        <Link className="btn btn-ghost" to="/payer/pay">All payment types</Link>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="panel stack" style={{ maxWidth: 560 }}>
        <div className="field">
          <label>Obligation</label>
          <select value={obligationId} onChange={(e) => setObligationId(e.target.value)}>
            {due.map((o) => (
              <option key={o.obligation_id} value={o.obligation_id}>
                {o.description} — {formatMoney(o.balance, o.currency)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Payment Channel</label>
          <select value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="MOBILE_MONEY">Mobile Money (Campay)</option>
            <option value="CARD">Card</option>
            <option value="OTHER">Other</option>
          </select>
        </div>
        {channel === 'MOBILE_MONEY' && (
          <div className="field">
            <label>MoMo phone number</label>
            <input
              required
              placeholder="2376XXXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <p className="muted">Collections are processed exclusively through Campay.</p>
          </div>
        )}
        {resolved && (
          <div className="stack">
            <div><span className="muted">Operating Area</span><br /><strong>{resolved.operating_area}</strong></div>
            <div><span className="muted">Council</span><br /><strong>{resolved.council_name}</strong></div>
            <div><span className="muted">Revenue</span><br /><strong>{resolved.revenue_name}</strong></div>
            <div><span className="muted">Amount Due</span><br /><strong>{formatMoney(resolved.amount, resolved.currency)}</strong></div>
            <div><span className="muted">Service Fee</span><br /><strong>{formatMoney(resolved.service_fee, resolved.currency)}</strong></div>
            <div><span className="muted">Total to Pay</span><br /><strong style={{ fontSize: '1.4rem' }}>{formatMoney(resolved.total_amount, resolved.currency)}</strong></div>
            <button className="btn btn-primary" type="button" disabled={loading} onClick={confirm}>
              {loading ? 'Processing…' : 'Confirm Payment'}
            </button>
          </div>
        )}
        {!due.length && <p className="muted">No outstanding obligations to pay.</p>}
      </div>
    </div>
  )
}
