import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function TenantRevenue() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState({ code: '', name: '', default_amount: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function load() {
    setRows(await api.revenueTypes())
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function create(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.post('/api/v1/revenue-types', {
        code: form.code,
        name: form.name,
        default_amount: form.default_amount || null,
      })
      setMessage('Revenue type created for current tenant context')
      setForm({ code: '', name: '', default_amount: '' })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="rise stack">
      <div>
        <h2>Revenue Setup</h2>
        <p className="muted">Tenant is applied from your session — no tenant_id field in the form.</p>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <form className="panel" onSubmit={create} style={{ maxWidth: 520 }}>
        <div className="field"><label>Code</label><input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></div>
        <div className="field"><label>Name</label><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
        <div className="field"><label>Default amount (XAF)</label><input value={form.default_amount} onChange={(e) => setForm({ ...form, default_amount: e.target.value })} /></div>
        <button className="btn btn-primary" type="submit">Add revenue type</button>
      </form>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Code</th><th>Name</th><th>Default</th><th>Status</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.revenue_type_id}>
                <td>{r.code}</td>
                <td>{r.name}</td>
                <td>{r.default_amount != null ? formatMoney(r.default_amount, r.currency) : '—'}</td>
                <td><span className="pill">{r.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
