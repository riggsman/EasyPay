import { useEffect, useId, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'

function iconGlyph(key) {
  if (key === 'droplet') return '💧'
  if (key === 'grid') return '▦'
  return '⚡'
}

function newIdem() {
  return `utl-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export default function ServicesStore() {
  const [services, setServices] = useState([])
  const [payer, setPayer] = useState(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [step, setStep] = useState('form') // form | processing | result
  const [refMode, setRefMode] = useState('METER')
  const [meterNumber, setMeterNumber] = useState('')
  const [billNumber, setBillNumber] = useState('')
  const [amount, setAmount] = useState('')
  const [phone, setPhone] = useState('')
  const [quote, setQuote] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const titleId = useId()

  useEffect(() => {
    Promise.all([api.utilityStore(), api.mePayer()])
      .then(([store, me]) => {
        setServices(listItems(store))
        setPayer(me)
        setPhone(me?.phone_number || '')
      })
      .catch((e) => setError(e.message))
  }, [])

  const canMeter = selected?.accept_meter_number
  const canBill = selected?.accept_bill_number

  useEffect(() => {
    if (!selected) return
    if (selected.accept_meter_number) setRefMode('METER')
    else if (selected.accept_bill_number) setRefMode('BILL')
  }, [selected])

  async function refreshQuote(nextAmount = amount) {
    if (!selected || !nextAmount) {
      setQuote(null)
      return
    }
    try {
      const q = await api.utilityQuote({
        utility_service_id: selected.utility_service_id,
        amount: Number(nextAmount),
      })
      setQuote(q)
    } catch (e) {
      setQuote(null)
      setError(e.message)
    }
  }

  function openService(svc) {
    setError('')
    setSelected(svc)
    setStep('form')
    setResult(null)
    setQuote(null)
    setAmount('')
    setMeterNumber('')
    setBillNumber('')
    setRefMode(svc.accept_meter_number ? 'METER' : 'BILL')
  }

  function closeModal() {
    if (busy) return
    setSelected(null)
    setStep('form')
    setResult(null)
  }

  async function onPay(e) {
    e.preventDefault()
    setError('')
    if (!selected) return
    if (refMode === 'METER' && !meterNumber.trim()) {
      setError('Enter a meter number')
      return
    }
    if (refMode === 'BILL' && !billNumber.trim()) {
      setError('Enter a bill number')
      return
    }
    setBusy(true)
    setStep('processing')
    try {
      const payload = {
        utility_service_id: selected.utility_service_id,
        amount: Number(amount),
        phone_number: phone,
        idempotency_key: newIdem(),
        meter_number: refMode === 'METER' ? meterNumber.trim() : null,
        bill_number: refMode === 'BILL' ? billNumber.trim() : null,
      }
      const res = await api.utilityPay(payload)
      setResult(res)
      setStep('result')
    } catch (err) {
      setError(err.message)
      setResult({ ok: false, status: 'FAILED', failure_reason: err.message })
      setStep('result')
    } finally {
      setBusy(false)
    }
  }

  const empty = useMemo(() => !services.length, [services])

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Services</h2>
          <p className="muted">Pay utility bills — only active services appear here.</p>
        </div>
        <Link className="btn btn-ghost" to="/payer/history">Transaction history</Link>
      </div>
      {error && !selected && <div className="alert">{error}</div>}

      {empty ? (
        <div className="panel muted">No services are available right now.</div>
      ) : (
        <div className="service-grid">
          {services.map((svc) => (
            <button
              key={svc.utility_service_id}
              type="button"
              className="service-card"
              style={{ '--svc-accent': svc.accent_color || '#1f6b4a' }}
              onClick={() => openService(svc)}
            >
              <span className="service-card-icon" aria-hidden="true">{iconGlyph(svc.icon_key)}</span>
              <strong>{svc.name}</strong>
              <span className="muted">{svc.description || svc.category}</span>
              <span className="pill">
                Fee {svc.fee_type === 'PERCENT' ? `${svc.fee_value}%` : formatMoney(svc.fee_value, svc.currency)}
              </span>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <div className="modal-backdrop" role="presentation" onClick={closeModal}>
          <div
            className="modal-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="app-top">
              <h3 id={titleId}>{selected.name}</h3>
              <button className="btn btn-ghost" type="button" onClick={closeModal} disabled={busy}>Close</button>
            </div>

            {step === 'form' && (
              <form onSubmit={onPay}>
                {error && <div className="alert">{error}</div>}
                <p className="muted">{selected.description}</p>
                <div className="field">
                  <label>Pay with</label>
                  <div className="row">
                    {canMeter && (
                      <button
                        type="button"
                        className={`btn ${refMode === 'METER' ? 'btn-primary' : 'btn-ghost'}`}
                        onClick={() => { setRefMode('METER'); setBillNumber('') }}
                      >
                        Meter number
                      </button>
                    )}
                    {canBill && (
                      <button
                        type="button"
                        className={`btn ${refMode === 'BILL' ? 'btn-primary' : 'btn-ghost'}`}
                        onClick={() => { setRefMode('BILL'); setMeterNumber('') }}
                      >
                        Bill number
                      </button>
                    )}
                  </div>
                </div>
                {refMode === 'METER' ? (
                  <div className="field">
                    <label>Meter number</label>
                    <input value={meterNumber} onChange={(e) => setMeterNumber(e.target.value)} required />
                  </div>
                ) : (
                  <div className="field">
                    <label>Bill number</label>
                    <input value={billNumber} onChange={(e) => setBillNumber(e.target.value)} required />
                  </div>
                )}
                <div className="field">
                  <label>Amount ({selected.currency})</label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={amount}
                    onChange={(e) => {
                      setAmount(e.target.value)
                      refreshQuote(e.target.value)
                    }}
                    onBlur={() => refreshQuote()}
                    required
                  />
                </div>
                <div className="field">
                  <label>Mobile Money phone</label>
                  <input value={phone} onChange={(e) => setPhone(e.target.value)} required />
                </div>
                {quote && (
                  <div className="panel" style={{ marginBottom: '1rem' }}>
                    <div>Bill: {formatMoney(quote.bill_amount, quote.currency)}</div>
                    <div>Service fee: {formatMoney(quote.service_fee, quote.currency)}</div>
                    <strong>Total: {formatMoney(quote.total_amount, quote.currency)}</strong>
                  </div>
                )}
                <button className="btn btn-primary" type="submit" disabled={busy}>
                  Pay now
                </button>
              </form>
            )}

            {step === 'processing' && (
              <div className="panel">
                <p>Processing Mobile Money debit…</p>
                <p className="muted">Confirm on your phone if prompted. Do not close this window.</p>
              </div>
            )}

            {step === 'result' && result && (
              <div>
                <div className={`alert ${result.ok ? 'ok' : ''}`}>
                  <strong>{result.ok ? 'Payment successful' : 'Payment failed'}</strong>
                  <div>{result.ok ? `${result.transaction_reference} settled.` : (result.failure_reason || result.status)}</div>
                </div>
                {result.ok && (
                  <div className="stack">
                    <p className="muted">
                      Receipt {result.receipt_number} recorded. A confirmation email is sent when email notifications are enabled.
                      The PDF is available from your receipts and transaction history.
                    </p>
                    <div className="row">
                      {result.receipt_id && (
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => api.downloadReceiptPdf(result.receipt_id, `${result.receipt_number}.pdf`).catch((e) => setError(e.message))}
                        >
                          Download PDF
                        </button>
                      )}
                      <Link className="btn btn-ghost" to={`/payer/payments/${result.transaction_id}`}>View transaction</Link>
                    </div>
                  </div>
                )}
                {!result.ok && (
                  <p className="muted">
                    This attempt is saved in your transaction history as failed
                    {result.transaction_reference ? ` (${result.transaction_reference})` : ''}.
                  </p>
                )}
                <div className="row" style={{ marginTop: '1rem' }}>
                  <button type="button" className="btn btn-ghost" onClick={closeModal}>Done</button>
                  {!result.ok && (
                    <button type="button" className="btn btn-primary" onClick={() => { setStep('form'); setResult(null); setError('') }}>
                      Try again
                    </button>
                  )}
                </div>
              </div>
            )}
            {payer && step === 'form' && (
              <p className="muted" style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
                Paying as {payer.business_name || payer.full_name}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
