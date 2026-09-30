import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'

export default function VerifyPage() {
  const { token: pathToken } = useParams()
  const [searchParams] = useSearchParams()
  const queryCode = searchParams.get('code') || searchParams.get('token') || ''
  const deepLinkToken = (pathToken || queryCode || '').trim()

  const [code, setCode] = useState(deepLinkToken)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function verifyValue(raw) {
    const value = (raw || '').trim()
    if (!value) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      // Deep-link / QR path uses the same public token verify endpoint
      if (value.startsWith('v_') || pathToken) {
        const data = await api.verifyToken(value)
        setResult(data)
        return
      }
      const looksLikeReceipt = value.toUpperCase().startsWith('RCPT')
      const data = await api.verify(
        looksLikeReceipt
          ? { receipt_number: value }
          : { verification_code: value },
      )
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (deepLinkToken) {
      setCode(deepLinkToken)
      verifyValue(deepLinkToken)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deepLinkToken])

  async function onSubmit(e) {
    e.preventDefault()
    await verifyValue(code)
  }

  return (
    <div className="container" style={{ padding: '2rem 0 4rem' }}>
      <div className="panel rise" style={{ maxWidth: 560, margin: '0 auto' }}>
        <h2>Verify Receipt</h2>
        <p>Enter a receipt number or verification code, or open a scanned QR link. No account required.</p>
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
