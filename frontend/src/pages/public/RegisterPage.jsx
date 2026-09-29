import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    full_name: '',
    business_name: '',
    email: '',
    phone_number: '',
    username: '',
    password: '',
    password_confirm: '',
    payer_type: 'BUSINESS',
    identification_type: 'NATIONAL_ID',
    identification_number: '',
    address: '',
    geographic_unit_id: '',
  })
  const [regions, setRegions] = useState([])
  const [towns, setTowns] = useState([])
  const [councils, setCouncils] = useState([])
  const [regionId, setRegionId] = useState('')
  const [townId, setTownId] = useState('')

  useEffect(() => {
    ;(async () => {
      const countries = await api.geographyChildren(null)
      const cm = countries.find((c) => c.unit_code === 'CM') || countries[0]
      if (!cm) return
      const regs = await api.geographyChildren(cm.geographic_unit_id)
      setRegions(regs)
    })().catch(() => {})
  }, [])

  useEffect(() => {
    if (!regionId) return
    ;(async () => {
      const divisions = await api.geographyChildren(regionId)
      const townsList = []
      for (const d of divisions) {
        const t = await api.geographyChildren(d.geographic_unit_id)
        townsList.push(...t)
      }
      setTowns(townsList)
      setTownId('')
      setCouncils([])
      setForm((f) => ({ ...f, geographic_unit_id: '' }))
    })().catch(() => {})
  }, [regionId])

  useEffect(() => {
    if (!townId) return
    ;(async () => {
      const c = await api.geographyChildren(townId)
      setCouncils(c)
      setForm((f) => ({ ...f, geographic_unit_id: '' }))
    })().catch(() => {})
  }, [townId])

  function update(key, value) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.register(form)
      navigate('/login')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-box panel rise" style={{ width: 'min(560px, calc(100% - 2rem))' }}>
      <h2>Create your account</h2>
      <div className="wizard-steps">
        <span className={step === 1 ? 'on' : ''}>1. Account</span>
        <span className={step === 2 ? 'on' : ''}>2. Business</span>
        <span className={step === 3 ? 'on' : ''}>3. Operating location</span>
      </div>
      {error && <div className="alert">{error}</div>}

      {step === 1 && (
        <div className="stack">
          <div className="field"><label>Full Name</label><input value={form.full_name} onChange={(e) => update('full_name', e.target.value)} /></div>
          <div className="field"><label>Email</label><input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} /></div>
          <div className="field"><label>Phone</label><input value={form.phone_number} onChange={(e) => update('phone_number', e.target.value)} /></div>
          <div className="field"><label>Username</label><input value={form.username} onChange={(e) => update('username', e.target.value)} /></div>
          <div className="field"><label>Password</label><input type="password" value={form.password} onChange={(e) => update('password', e.target.value)} /></div>
          <div className="field"><label>Confirm Password</label><input type="password" value={form.password_confirm} onChange={(e) => update('password_confirm', e.target.value)} /></div>
          <button className="btn btn-primary" type="button" onClick={() => setStep(2)}>Continue</button>
        </div>
      )}

      {step === 2 && (
        <div className="stack">
          <div className="field">
            <label>Payer Type</label>
            <select value={form.payer_type} onChange={(e) => update('payer_type', e.target.value)}>
              <option value="INDIVIDUAL">Individual</option>
              <option value="BUSINESS">Business</option>
            </select>
          </div>
          <div className="field"><label>Business / Organization</label><input value={form.business_name} onChange={(e) => update('business_name', e.target.value)} /></div>
          <div className="field"><label>Identification Type</label><input value={form.identification_type} onChange={(e) => update('identification_type', e.target.value)} /></div>
          <div className="field"><label>Identification Number</label><input value={form.identification_number} onChange={(e) => update('identification_number', e.target.value)} /></div>
          <div className="field"><label>Business Address</label><textarea rows={2} value={form.address} onChange={(e) => update('address', e.target.value)} /></div>
          <div className="row">
            <button className="btn btn-ghost" type="button" onClick={() => setStep(1)}>Back</button>
            <button className="btn btn-primary" type="button" onClick={() => setStep(3)}>Continue</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <form onSubmit={submit} className="stack">
          <p>Where do you currently operate?</p>
          <div className="field">
            <label>Region</label>
            <select value={regionId} onChange={(e) => setRegionId(e.target.value)} required>
              <option value="">Select region</option>
              {regions.map((r) => <option key={r.geographic_unit_id} value={r.geographic_unit_id}>{r.unit_name}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Town / Municipality</label>
            <select value={townId} onChange={(e) => setTownId(e.target.value)} required>
              <option value="">Select town</option>
              {towns.map((t) => <option key={t.geographic_unit_id} value={t.geographic_unit_id}>{t.unit_name}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Council / Zone</label>
            <select value={form.geographic_unit_id} onChange={(e) => update('geographic_unit_id', e.target.value)} required>
              <option value="">Select council</option>
              {councils.map((c) => <option key={c.geographic_unit_id} value={c.geographic_unit_id}>{c.unit_name}</option>)}
            </select>
          </div>
          <div className="row">
            <button className="btn btn-ghost" type="button" onClick={() => setStep(2)}>Back</button>
            <button className="btn btn-primary" type="submit" disabled={loading}>{loading ? 'Creating…' : 'Create Account'}</button>
          </div>
        </form>
      )}

      <p style={{ marginTop: '1rem' }}><Link to="/login">Already have an account? Sign in</Link></p>
    </div>
  )
}
