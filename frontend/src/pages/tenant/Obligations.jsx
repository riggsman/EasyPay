import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'
import { useAuth } from '../../contexts/AuthContext'

export default function TenantObligations() {
  const { tenantId } = useAuth()
  const [rows, setRows] = useState([])
  const [revenues, setRevenues] = useState([])
  const [form, setForm] = useState({ payer_id: '', revenue_type_id: '', amount: '', description: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function load() {
    const [o, r] = await Promise.all([api.obligations(), api.revenueTypes()])
    setRows(o)
    setRevenues(r)
    if (r[0]) setForm((f) => ({ ...f, revenue_type_id: f.revenue_type_id || r[0].revenue_type_id }))
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function create(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.createObligation({
        payer_id: form.payer_id,
        revenue_type_id: form.revenue_type_id,
        amount: form.amount,
        description: form.description || undefined,
      })
      setMessage('Obligation created. Geographic/tenant snapshot taken from the payer’s current zone.')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="rise stack">
      <div>
        <h2>Obligations</h2>
        <p className="muted">
          Creating an obligation snapshots the payer’s current council/zone. Tenant context: locked from session
          {tenantId ? ` (${tenantId.slice(0, 12)}…)` : ''}.
        </p>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <form className="panel" onSubmit={create} style={{ maxWidth: 560 }}>
        <div className="field"><label>Payer ID</label><input required value={form.payer_id} onChange={(e) => setForm({ ...form, payer_id: e.target.value })} placeholder="pay_…" /></div>
        <div className="field">
          <label>Revenue type</label>
          <select required value={form.revenue_type_id} onChange={(e) => setForm({ ...form, revenue_type_id: e.target.value })}>
            {revenues.map((r) => <option key={r.revenue_type_id} value={r.revenue_type_id}>{r.name}</option>)}
          </select>
        </div>
        <div className="field"><label>Amount</label><input required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></div>
        <div className="field"><label>Description</label><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
        <button className="btn btn-primary" type="submit">Create obligation</button>
      </form>
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Description</th><th>Payer</th><th>Amount</th><th>Balance</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.obligation_id}>
                <td>{o.description}</td>
                <td className="muted">{o.payer_id.slice(0, 12)}…</td>
                <td>{formatMoney(o.amount)}</td>
                <td>{formatMoney(o.balance)}</td>
                <td><span className="pill">{o.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
