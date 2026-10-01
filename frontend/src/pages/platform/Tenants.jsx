import { useEffect, useMemo, useRef, useState } from 'react'
import { api, listItems } from '../../api/client'

const EMPTY = {
  tenant_code: '',
  organization_name: '',
  organization_type: 'COUNCIL',
  email: '',
  phone_number: '',
  currency: 'XAF',
  zone_change_mode: 'IMMEDIATE',
  geographic_unit_id: '',
}

function TenantLogoThumb({ tenantId, hasLogo, bust }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    let alive = true
    let objectUrl = ''
    if (!hasLogo) {
      setUrl('')
      return undefined
    }
    api
      .tenantLogoBlob(tenantId)
      .then((blob) => {
        if (!alive) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(() => {
        if (alive) setUrl('')
      })
    return () => {
      alive = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [tenantId, hasLogo, bust])

  if (!hasLogo || !url) {
    return <span className="muted" style={{ fontSize: '0.85rem' }}>—</span>
  }
  return (
    <img
      src={url}
      alt=""
      width={36}
      height={36}
      style={{ width: 36, height: 36, objectFit: 'contain', borderRadius: 8, background: '#edf5f0' }}
    />
  )
}

export default function PlatformTenants() {
  const formRef = useRef(null)
  const fileRef = useRef(null)
  const [rows, setRows] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [logoFile, setLogoFile] = useState(null)
  const [logoPreview, setLogoPreview] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [logoBust, setLogoBust] = useState(0)

  const [regions, setRegions] = useState([])
  const [divisions, setDivisions] = useState([])
  const [councils, setCouncils] = useState([])
  const [regionId, setRegionId] = useState('')
  const [divisionId, setDivisionId] = useState('')

  async function load() {
    const data = await api.tenants()
    setRows(listItems(data))
  }

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function resetForm() {
    setForm(EMPTY)
    setLogoFile(null)
    setLogoPreview('')
    setRegionId('')
    setDivisionId('')
    setDivisions([])
    setCouncils([])
    if (fileRef.current) fileRef.current.value = ''
  }

  function onLogoChange(e) {
    const file = e.target.files?.[0] || null
    setLogoFile(file)
    if (logoPreview) URL.revokeObjectURL(logoPreview)
    setLogoPreview(file ? URL.createObjectURL(file) : '')
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
    ;(async () => {
      const countries = await api.geographyChildren(null)
      const cm = countries.find((c) => c.unit_code === 'CM') || countries[0]
      if (!cm) return
      setRegions(await api.geographyChildren(cm.geographic_unit_id))
    })().catch(() => {})
    return () => {
      if (logoPreview) URL.revokeObjectURL(logoPreview)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!regionId) {
      setDivisions([])
      setDivisionId('')
      setCouncils([])
      setField('geographic_unit_id', '')
      return
    }
    api
      .geographyChildren(regionId)
      .then((rows) => {
        setDivisions(rows)
        setDivisionId('')
        setCouncils([])
        setField('geographic_unit_id', '')
      })
      .catch(() => {})
  }, [regionId])

  useEffect(() => {
    if (!divisionId) {
      setCouncils([])
      setField('geographic_unit_id', '')
      return
    }
    api
      .geographyChildren(divisionId)
      .then((rows) => {
        // Prefer COUNCIL leaves; fall back to whatever children exist (towns → councils)
        const councilRows = rows.filter((r) => r.unit_type === 'COUNCIL')
        if (councilRows.length) {
          setCouncils(councilRows)
          setField('geographic_unit_id', '')
          return
        }
        Promise.all(rows.map((t) => api.geographyChildren(t.geographic_unit_id)))
          .then((nested) => {
            setCouncils(nested.flat().filter((r) => r.unit_type === 'COUNCIL'))
            setField('geographic_unit_id', '')
          })
          .catch(() => setCouncils([]))
      })
      .catch(() => {})
  }, [divisionId])

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const fd = new FormData()
      fd.append('tenant_code', form.tenant_code.trim().toUpperCase())
      fd.append('organization_name', form.organization_name.trim())
      fd.append('organization_type', form.organization_type)
      if (form.email.trim()) fd.append('email', form.email.trim())
      if (form.phone_number.trim()) fd.append('phone_number', form.phone_number.trim())
      fd.append('currency', form.currency)
      fd.append('zone_change_mode', form.zone_change_mode)
      if (form.geographic_unit_id) fd.append('geographic_unit_id', form.geographic_unit_id)
      if (logoFile) fd.append('logo', logoFile)

      await api.registerTenant(fd)
      setMessage(
        logoFile
          ? 'Tenant registered with logo — it will appear on receipts and PDFs.'
          : 'Tenant registered. You can upload a logo later from the table.',
      )
      resetForm()
      setLogoBust((n) => n + 1)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function uploadExistingLogo(tenant, file) {
    if (!file) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await api.uploadTenantLogo(tenant.tenant_id, file)
      setMessage(`Logo updated for ${tenant.organization_name}`)
      setLogoBust((n) => n + 1)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const sorted = useMemo(
    () => [...rows].sort((a, b) => String(a.organization_name).localeCompare(String(b.organization_name))),
    [rows],
  )

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Tenants / Councils</h2>
          <p className="muted">Register tenants and upload their logo for receipts and PDF branding.</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => {
            resetForm()
            setMessage('')
            setError('')
            formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            window.setTimeout(() => formRef.current?.querySelector('input')?.focus(), 80)
          }}
        >
          Register tenant
        </button>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}

      <div className="panel" ref={formRef} style={{ marginBottom: '1.25rem' }}>
        <h3>Register tenant</h3>
        <form onSubmit={onSubmit}>
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <div className="field" style={{ flex: 1, minWidth: 140 }}>
              <label>Tenant code</label>
              <input
                value={form.tenant_code}
                onChange={(e) => setField('tenant_code', e.target.value)}
                required
                placeholder="e.g. DOUALA1"
              />
            </div>
            <div className="field" style={{ flex: 2, minWidth: 200 }}>
              <label>Organization name</label>
              <input
                value={form.organization_name}
                onChange={(e) => setField('organization_name', e.target.value)}
                required
                placeholder="e.g. Douala 1 Council"
              />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 140 }}>
              <label>Type</label>
              <select value={form.organization_type} onChange={(e) => setField('organization_type', e.target.value)}>
                <option value="COUNCIL">COUNCIL</option>
                <option value="BUSINESS">BUSINESS</option>
                <option value="UTILITY">UTILITY</option>
                <option value="OTHER">OTHER</option>
              </select>
            </div>
          </div>

          <div className="row">
            <div className="field" style={{ flex: 1 }}>
              <label>Email</label>
              <input type="email" value={form.email} onChange={(e) => setField('email', e.target.value)} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Phone</label>
              <input value={form.phone_number} onChange={(e) => setField('phone_number', e.target.value)} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Currency</label>
              <input value={form.currency} onChange={(e) => setField('currency', e.target.value)} required />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Zone change</label>
              <select value={form.zone_change_mode} onChange={(e) => setField('zone_change_mode', e.target.value)}>
                <option value="IMMEDIATE">IMMEDIATE</option>
                <option value="APPROVAL_REQUIRED">APPROVAL_REQUIRED</option>
              </select>
            </div>
          </div>

          <div className="row">
            <div className="field" style={{ flex: 1 }}>
              <label>Region</label>
              <select value={regionId} onChange={(e) => setRegionId(e.target.value)}>
                <option value="">Optional</option>
                {regions.map((r) => (
                  <option key={r.geographic_unit_id} value={r.geographic_unit_id}>
                    {r.unit_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Division</label>
              <select value={divisionId} onChange={(e) => setDivisionId(e.target.value)} disabled={!regionId}>
                <option value="">Optional</option>
                {divisions.map((d) => (
                  <option key={d.geographic_unit_id} value={d.geographic_unit_id}>
                    {d.unit_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label>Primary council / zone</label>
              <select
                value={form.geographic_unit_id}
                onChange={(e) => setField('geographic_unit_id', e.target.value)}
                disabled={!councils.length}
              >
                <option value="">Optional</option>
                {councils.map((c) => (
                  <option key={c.geographic_unit_id} value={c.geographic_unit_id}>
                    {c.unit_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="row" style={{ alignItems: 'flex-end' }}>
            <div className="field" style={{ flex: 2 }}>
              <label>Logo / image (optional, PNG/JPG, max 2MB)</label>
              <input ref={fileRef} type="file" accept="image/*" onChange={onLogoChange} />
            </div>
            {logoPreview ? (
              <div className="field" style={{ flex: '0 0 auto' }}>
                <label>Preview</label>
                <img
                  src={logoPreview}
                  alt="Logo preview"
                  width={64}
                  height={64}
                  style={{ width: 64, height: 64, objectFit: 'contain', borderRadius: 10, background: '#edf5f0' }}
                />
              </div>
            ) : null}
          </div>

          <div className="row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? 'Saving…' : 'Register tenant'}
            </button>
            <button className="btn btn-ghost" type="button" disabled={busy} onClick={resetForm}>
              Clear
            </button>
          </div>
        </form>
      </div>

      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Logo</th>
              <th>Code</th>
              <th>Name</th>
              <th>Type</th>
              <th>Currency</th>
              <th>Zone change</th>
              <th>Status</th>
              <th>Update logo</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t) => (
              <tr key={t.tenant_id}>
                <td>
                  <TenantLogoThumb tenantId={t.tenant_id} hasLogo={!!t.logo_path} bust={logoBust} />
                </td>
                <td>{t.tenant_code}</td>
                <td>{t.organization_name}</td>
                <td>{t.organization_type}</td>
                <td>{t.currency}</td>
                <td>{t.zone_change_mode}</td>
                <td>
                  <span className="pill">{t.status}</span>
                </td>
                <td>
                  <label className="btn btn-ghost" style={{ cursor: busy ? 'wait' : 'pointer', margin: 0 }}>
                    Upload
                    <input
                      type="file"
                      accept="image/*"
                      hidden
                      disabled={busy}
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        e.target.value = ''
                        uploadExistingLogo(t, file)
                      }}
                    />
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
