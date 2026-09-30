import { useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function VerifyPage() {
  const [code, setCode] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const looksLikeReceipt = code.toUpperCase().startsWith('RCPT')
      const data = await api.verify(
        looksLikeReceipt
          ? { receipt_number: code.trim() }
          : { verification_code: code.trim() },
      )
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container" style={{ padding: '2rem 0 4rem' }}>
      <div className="panel rise" style={{ maxWidth: 560, margin: '0 auto' }}>
        <h2>Verify Receipt</h2>
        <p>Enter a receipt number or verification code. No account required.</p>
        {error && <div className="alert">{error}</div>}
        <form onSubmit={onSubmit}>
          <div className="field">
            <label>Receipt Number or Verification Code</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} required placeholder="RCPT-2026-…" />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Verifying…' : 'Verify'}
          </button>
        </form>
        {result && (
          <div className={`alert ${result.verified ? 'ok' : ''}`} style={{ marginTop: '1.25rem' }}>
            <strong>{result.verified ? '✓ VERIFIED' : '✕ NOT VERIFIED'}</strong>
            <div>{result.message}</div>
            {result.verified && (
              <div style={{ marginTop: '0.75rem' }}>
                <div>Receipt: {result.receipt_number}</div>
                <div>Council: {result.council_name}</div>
                <div>Revenue: {result.revenue_name}</div>
                <div>Amount: {formatMoney(result.amount, result.currency)}</div>
                <div>Total: {formatMoney(result.total_amount, result.currency)}</div>
                <div>Payer: {result.payer_display}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
