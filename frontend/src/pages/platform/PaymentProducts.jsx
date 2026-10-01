import { useEffect, useState } from 'react'
import { api, listItems } from '../../api/client'

/**
 * Platform admin: enable/disable/order payment product cards on Make Payment.
 * New future products can be registered with a payer route_path.
 */
export default function PaymentProductsAdmin() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    code: '',
    name: '',
    description: '',
    route_path: '/payer/pay/',
    icon_key: 'wallet',
    accent_color: '#1f6b4a',
    requires_catalog: false,
    catalog_type: '',
    sort_order: 50,
    status: 'ACTIVE',
  })

  async function load() {
    const rows = await api.paymentProductsAdmin()
    setItems(listItems(rows))
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function toggle(row) {
    setBusy(true)
    setError('')
    try {
      const next = row.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
      await api.updatePaymentProduct(row.payment_product_id, { status: next })
      await load()
      setMessage(next === 'ACTIVE' ? `${row.name} enabled on Make Payment` : `${row.name} hidden from Make Payment`)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function onCreate(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await api.createPaymentProduct({
        ...form,
        code: form.code.trim().toUpperCase(),
        catalog_type: form.catalog_type || null,
        sort_order: Number(form.sort_order),
      })
      setMessage('Payment product created — ACTIVE products show on Make Payment')
      setForm((f) => ({ ...f, code: '', name: '', description: '' }))
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Payment products</h2>
          <p className="muted">
            Cards on the payer Make Payment screen. Add future types with a route (e.g. /payer/pay/school-fees).
            Catalog-backed products (utilities) only appear when their store has active services.
          </p>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}

      <div className="panel" style={{ marginBottom: '1.25rem' }}>
        <h3>Register a payment product</h3>
        <form onSubmit={onCreate}>
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <div className="field" style={{ flex: 1 }}>
              <label>Code</label>
              <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required placeholder="SCHOOL" />
            </div>
            <div className="field" style={{ flex: 2 }}>
              <label>Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="field" style={{ flex: 2 }}>
              <label>Route path</label>
              <input value={form.route_path} onChange={(e) => setForm({ ...form, route_path: e.target.value })} required />
            </div>
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="row">
            <label>
              <input
                type="checkbox"
                checked={form.requires_catalog}
                onChange={(e) => setForm({ ...form, requires_catalog: e.target.checked })}
              />{' '}
              Requires catalog items
            </label>
            <div className="field" style={{ margin: 0 }}>
              <label>Catalog type</label>
              <input
                value={form.catalog_type}
                onChange={(e) => setForm({ ...form, catalog_type: e.target.value })}
                placeholder="UTILITY"
              />
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label>Sort</label>
              <input type="number" value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: e.target.value })} />
            </div>
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy}>Create product</button>
        </form>
      </div>

      <div className="table-wrap panel">
        <table className="data">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Route</th>
              <th>Catalog</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.payment_product_id}>
                <td>{row.code}</td>
                <td>
                  <strong>{row.name}</strong>
                  <div className="muted" style={{ fontSize: '0.85rem' }}>{row.description}</div>
                </td>
                <td><code>{row.route_path}</code></td>
                <td>{row.requires_catalog ? row.catalog_type || 'yes' : '—'}</td>
                <td><span className={`pill${row.status !== 'ACTIVE' ? ' failed' : ''}`}>{row.status}</span></td>
                <td>
                  <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => toggle(row)}>
                    {row.status === 'ACTIVE' ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
