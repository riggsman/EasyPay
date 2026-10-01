import { useEffect, useState } from 'react'
import { api, formatMoney, listItems } from '../../api/client'

const EMPTY = {
  code: '',
  name: '',
  description: '',
  category: 'ELECTRICITY',
  icon_key: 'bolt',
  accent_color: '#1f6b4a',
  fee_type: 'FLAT',
  fee_value: '500',
  currency: 'XAF',
  accept_meter_number: true,
  accept_bill_number: true,
  sort_order: 50,
  status: 'ACTIVE',
}

export default function UtilityServicesAdmin() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editingId, setEditingId] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const rows = await api.utilityServicesAdmin()
    setItems(listItems(rows))
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function startEdit(row) {
    setEditingId(row.utility_service_id)
    setForm({
      code: row.code,
      name: row.name,
      description: row.description || '',
      category: row.category,
      icon_key: row.icon_key,
      accent_color: row.accent_color,
      fee_type: row.fee_type,
      fee_value: String(row.fee_value),
      currency: row.currency,
      accept_meter_number: !!row.accept_meter_number,
      accept_bill_number: !!row.accept_bill_number,
      sort_order: row.sort_order,
      status: row.status,
    })
    setMessage('')
    setError('')
  }

  function resetForm() {
    setEditingId(null)
    setForm(EMPTY)
  }

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const payload = {
        ...form,
        fee_value: Number(form.fee_value),
        sort_order: Number(form.sort_order),
        code: form.code.trim().toUpperCase(),
      }
      if (editingId) {
        const { code: _c, ...patch } = payload
        await api.updateUtilityService(editingId, patch)
        setMessage('Service updated — store cards refresh for active services only')
      } else {
        await api.createUtilityService(payload)
        setMessage('Service created — it appears in the payer store when ACTIVE')
      }
      resetForm()
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function toggleStatus(row) {
    const next = row.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
    setBusy(true)
    try {
      await api.updateUtilityService(row.utility_service_id, { status: next })
      await load()
      setMessage(next === 'ACTIVE' ? 'Service enabled in store' : 'Service hidden from store')
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
          <h2>Utility services</h2>
          <p className="muted">
            Platform catalog for bill-pay (light, water, …). Active services become store cards automatically; disabled services are hidden.
          </p>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}

      <div className="panel" style={{ marginBottom: '1.25rem' }}>
        <h3>{editingId ? 'Edit service' : 'Add service'}</h3>
        <form onSubmit={onSubmit}>
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <div className="field" style={{ flex: 1, minWidth: 160 }}>
              <label>Code</label>
              <input value={form.code} onChange={(e) => setField('code', e.target.value)} required disabled={!!editingId} />
            </div>
            <div className="field" style={{ flex: 2, minWidth: 200 }}>
              <label>Name</label>
              <input value={form.name} onChange={(e) => setField('name', e.target.value)} required />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 140 }}>
              <label>Category</label>
              <select value={form.category} onChange={(e) => setField('category', e.target.value)}>
                <option value="ELECTRICITY">ELECTRICITY</option>
                <option value="WATER">WATER</option>
                <option value="OTHER">OTHER</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label>Description</label>
            <textarea value={form.description} onChange={(e) => setField('description', e.target.value)} rows={2} />
          </div>
          <div className="row">
            <div className="field">
              <label>Fee type</label>
              <select value={form.fee_type} onChange={(e) => setField('fee_type', e.target.value)}>
                <option value="FLAT">FLAT</option>
                <option value="PERCENT">PERCENT</option>
              </select>
            </div>
            <div className="field">
              <label>Fee value</label>
              <input type="number" step="0.01" value={form.fee_value} onChange={(e) => setField('fee_value', e.target.value)} required />
            </div>
            <div className="field">
              <label>Currency</label>
              <input value={form.currency} onChange={(e) => setField('currency', e.target.value)} />
            </div>
            <div className="field">
              <label>Sort</label>
              <input type="number" value={form.sort_order} onChange={(e) => setField('sort_order', e.target.value)} />
            </div>
            <div className="field">
              <label>Accent</label>
              <input type="color" value={form.accent_color} onChange={(e) => setField('accent_color', e.target.value)} />
            </div>
          </div>
          <div className="row" style={{ marginBottom: '1rem' }}>
            <label><input type="checkbox" checked={form.accept_meter_number} onChange={(e) => setField('accept_meter_number', e.target.checked)} /> Meter number</label>
            <label><input type="checkbox" checked={form.accept_bill_number} onChange={(e) => setField('accept_bill_number', e.target.checked)} /> Bill number</label>
            <div className="field" style={{ margin: 0 }}>
              <label>Status</label>
              <select value={form.status} onChange={(e) => setField('status', e.target.value)}>
                <option value="ACTIVE">ACTIVE</option>
                <option value="DISABLED">DISABLED</option>
              </select>
            </div>
          </div>
          <div className="row">
            <button className="btn btn-primary" type="submit" disabled={busy}>{editingId ? 'Save changes' : 'Create service'}</button>
            {editingId && <button className="btn btn-ghost" type="button" onClick={resetForm}>Cancel</button>}
          </div>
        </form>
      </div>

      <div className="table-wrap panel">
        <table className="data">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Fee</th>
              <th>Refs</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.utility_service_id}>
                <td>{row.code}</td>
                <td>
                  <strong>{row.name}</strong>
                  <div className="muted" style={{ fontSize: '0.85rem' }}>{row.category}</div>
                </td>
                <td>
                  {row.fee_type === 'PERCENT'
                    ? `${row.fee_value}%`
                    : formatMoney(row.fee_value, row.currency)}
                </td>
                <td>
                  {row.accept_meter_number ? 'Meter ' : ''}
                  {row.accept_bill_number ? 'Bill' : ''}
                </td>
                <td><span className={`pill${row.status !== 'ACTIVE' ? ' failed' : ''}`}>{row.status}</span></td>
                <td className="row">
                  <button type="button" className="btn btn-ghost" onClick={() => startEdit(row)}>Edit</button>
                  <button type="button" className="btn btn-ghost" onClick={() => toggleStatus(row)} disabled={busy}>
                    {row.status === 'ACTIVE' ? 'Disable' : 'Enable'}
                  </button>
                </td>
              </tr>
            ))}
            {!items.length && (
              <tr><td colSpan={6} className="muted">No services yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
