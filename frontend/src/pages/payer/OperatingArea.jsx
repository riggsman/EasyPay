import { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function OperatingAreaPage() {
  const [area, setArea] = useState(null)
  const [councils, setCouncils] = useState([])
  const [newZone, setNewZone] = useState('')
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    const a = await api.operatingArea()
    setArea(a)
    // load sibling councils under same town
    const path = a.ancestry?.path || []
    const town = path.find((p) => p.type === 'TOWN' || p.type === 'MUNICIPALITY')
    if (town) {
      const kids = await api.geographyChildren(town.id)
      setCouncils(kids)
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function submit(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      const res = await api.changeZone({ geographic_unit_id: newZone, reason })
      setMessage(res.message || `Zone updated (${res.mode})`)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const leaf = area?.ancestry?.path?.slice(-1)?.[0]

  return (
    <div className="rise stack">
      <h2>Operating Area</h2>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <div className="panel">
        <h3>Current</h3>
        <p>
          {(area?.ancestry?.path || []).map((p) => p.name).join(' → ') || '—'}
        </p>
        <span className="pill">{leaf?.name}</span>
      </div>
      <form className="panel stack" onSubmit={submit} style={{ maxWidth: 520 }}>
        <h3>Change Operating Area</h3>
        <div className="field">
          <label>New Council</label>
          <select value={newZone} onChange={(e) => setNewZone(e.target.value)} required>
            <option value="">Select</option>
            {councils.map((c) => (
              <option key={c.geographic_unit_id} value={c.geographic_unit_id}>{c.unit_name}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Reason</label>
          <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
        </div>
        <button className="btn btn-primary" type="submit">Submit Change</button>
      </form>
      <div className="panel">
        <h3>History</h3>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr><th>Zone ID</th><th>From</th><th>To</th><th>Reason</th></tr>
            </thead>
            <tbody>
              {(area?.history || []).map((h) => (
                <tr key={h.payer_geographic_history_id}>
                  <td>{h.geographic_unit_id}</td>
                  <td>{new Date(h.effective_from).toLocaleDateString()}</td>
                  <td>{h.effective_to ? new Date(h.effective_to).toLocaleDateString() : 'Current'}</td>
                  <td>{h.change_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
