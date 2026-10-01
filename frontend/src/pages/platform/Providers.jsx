import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { EmptyRow, PageHeader } from '../../components/OpsUI'
import { useAuth } from '../../contexts/AuthContext'

function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  )
}

const TABS = [
  { id: 'campay', label: 'Campay' },
  { id: 'email', label: 'Email' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'sms', label: 'SMS' },
  { id: 'overview', label: 'Overview' },
]

export default function PlatformProviders() {
  const { userType } = useAuth()
  const allowed = userType === 'SUPER_ADMIN' || userType === 'PLATFORM_ADMIN'
  const [tab, setTab] = useState('campay')
  const [campay, setCampay] = useState({
    enabled: true,
    username: '',
    password: '',
    base_url: 'https://demo.campay.net/api',
    mock: true,
    bank_transfer_path: '/withdraw/',
  })
  const [email, setEmail] = useState({
    enabled: true,
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    smtp_from: '',
    smtp_use_tls: true,
  })
  const [whatsapp, setWhatsapp] = useState({
    enabled: true,
    api_url: '',
    api_key: '',
  })
  const [sms, setSms] = useState({
    enabled: false,
    api_url: '',
    api_key: '',
  })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [meta, setMeta] = useState({})

  async function load() {
    const rows = await api.providers()
    const byCode = Object.fromEntries(rows.map((r) => [r.provider_code, r]))
    setMeta(byCode)
    const c = byCode.CAMPAY?.settings || {}
    setCampay((prev) => ({
      ...prev,
      enabled: Boolean(byCode.CAMPAY?.enabled),
      username: c.username || '',
      password: '',
      base_url: c.base_url || prev.base_url,
      mock: c.mock !== undefined ? Boolean(c.mock) : true,
      bank_transfer_path: c.bank_transfer_path || '/withdraw/',
    }))
    const e = byCode.EMAIL?.settings || {}
    setEmail((prev) => ({
      ...prev,
      enabled: Boolean(byCode.EMAIL?.enabled),
      smtp_host: e.smtp_host || '',
      smtp_port: String(e.smtp_port || '587'),
      smtp_user: e.smtp_user || '',
      smtp_password: '',
      smtp_from: e.smtp_from || '',
      smtp_use_tls: e.smtp_use_tls !== undefined ? Boolean(e.smtp_use_tls) : true,
    }))
    const w = byCode.WHATSAPP?.settings || {}
    setWhatsapp((prev) => ({
      ...prev,
      enabled: Boolean(byCode.WHATSAPP?.enabled),
      api_url: w.api_url || '',
      api_key: '',
    }))
    const s = byCode.SMS?.settings || {}
    setSms((prev) => ({
      ...prev,
      enabled: Boolean(byCode.SMS?.enabled),
      api_url: s.api_url || '',
      api_key: '',
    }))
  }

  useEffect(() => {
    if (!allowed) return
    load().catch((e) => setError(e.message))
  }, [allowed])

  function selectTab(id) {
    setTab(id)
    setError('')
    setMessage('')
  }

  if (!allowed) {
    return <div className="alert">Provider configuration is restricted to system / super administrators.</div>
  }

  async function saveCampay(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.upsertCampay({
        enabled: campay.enabled,
        display_name: 'Campay',
        settings: {
          username: campay.username,
          password: campay.password,
          base_url: campay.base_url,
          mock: campay.mock,
          bank_transfer_path: campay.bank_transfer_path,
        },
        public_meta: { environment: campay.mock ? 'sandbox' : 'live' },
      })
      setMessage('Campay configuration saved (encrypted at rest)')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function saveEmail(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.upsertEmailProvider({
        enabled: email.enabled,
        display_name: 'Email SMTP',
        settings: {
          smtp_host: email.smtp_host,
          smtp_port: email.smtp_port,
          smtp_user: email.smtp_user,
          smtp_password: email.smtp_password,
          smtp_from: email.smtp_from,
          smtp_use_tls: email.smtp_use_tls,
        },
      })
      setMessage('Email SMTP configuration saved (encrypted at rest)')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function saveWhatsapp(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.upsertWhatsappProvider({
        enabled: whatsapp.enabled,
        display_name: 'WhatsApp',
        settings: {
          api_url: whatsapp.api_url,
          api_key: whatsapp.api_key,
        },
      })
      setMessage('WhatsApp configuration saved (encrypted at rest)')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function saveSms(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.upsertSmsProvider({
        enabled: sms.enabled,
        display_name: 'SMS',
        settings: {
          api_url: sms.api_url,
          api_key: sms.api_key,
        },
      })
      setMessage('SMS configuration saved (encrypted at rest)')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  async function testToken() {
    setError('')
    setMessage('')
    try {
      const res = await api.testCampayToken()
      setMessage(`Campay token OK${res.mock ? ' (mock)' : ''}: ${res.token_preview || 'received'}`)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="rise stack">
      <PageHeader
        title="Provider configuration"
        subtitle="Campay MoMo, Email, and WhatsApp credentials are encrypted in the database. Super/system admin only."
      />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}

      <div className="ops-tabs" role="tablist" aria-label="Provider configuration sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`ops-tab${tab === t.id ? ' on' : ''}`}
            onClick={() => selectTab(t.id)}
          >
            {t.label}
            {t.id !== 'overview' && meta[t.id.toUpperCase()]?.configured ? ' · ✓' : ''}
          </button>
        ))}
      </div>

      {tab === 'campay' && (
        <div role="tabpanel" className="stack">
          <p className="muted">
            All MOBILE_MONEY payer collections and MoMo/bank settlement payouts are routed through Campay.
            {meta.CAMPAY?.configured ? ' Credentials on file (masked).' : ' Not configured yet.'}
          </p>
          <form className="panel stack" onSubmit={saveCampay} style={{ maxWidth: 640 }}>
            <label className="row">
              <input type="checkbox" checked={campay.enabled} onChange={(e) => setCampay({ ...campay, enabled: e.target.checked })} />
              Enable Campay
            </label>
            <label className="row">
              <input type="checkbox" checked={campay.mock} onChange={(e) => setCampay({ ...campay, mock: e.target.checked })} />
              Mock mode (sandbox / no live HTTP)
            </label>
            <Field label="API base URL">
              <input value={campay.base_url} onChange={(e) => setCampay({ ...campay, base_url: e.target.value })} required />
            </Field>
            <Field label="Username / App username">
              <input value={campay.username} onChange={(e) => setCampay({ ...campay, username: e.target.value })} placeholder={meta.CAMPAY?.settings?.username || ''} />
            </Field>
            <Field label="Password / App password">
              <input
                type="password"
                value={campay.password}
                onChange={(e) => setCampay({ ...campay, password: e.target.value })}
                placeholder={meta.CAMPAY?.settings?.password_configured ? '•••• stored' : ''}
              />
            </Field>
            <Field label="Bank transfer path (Campay bank service)">
              <input value={campay.bank_transfer_path} onChange={(e) => setCampay({ ...campay, bank_transfer_path: e.target.value })} />
            </Field>
            <div className="row">
              <button className="btn btn-primary" type="submit">Save Campay (encrypt)</button>
              <button className="btn btn-ghost" type="button" onClick={testToken}>Test token</button>
            </div>
          </form>
        </div>
      )}

      {tab === 'email' && (
        <div role="tabpanel" className="stack">
          <p className="muted">SMTP credentials are encrypted at rest.</p>
          <form className="panel stack" onSubmit={saveEmail} style={{ maxWidth: 640 }}>
            <label className="row">
              <input type="checkbox" checked={email.enabled} onChange={(e) => setEmail({ ...email, enabled: e.target.checked })} />
              Enable email provider
            </label>
            <Field label="SMTP host"><input value={email.smtp_host} onChange={(e) => setEmail({ ...email, smtp_host: e.target.value })} /></Field>
            <Field label="SMTP port"><input value={email.smtp_port} onChange={(e) => setEmail({ ...email, smtp_port: e.target.value })} /></Field>
            <Field label="SMTP user"><input value={email.smtp_user} onChange={(e) => setEmail({ ...email, smtp_user: e.target.value })} /></Field>
            <Field label="SMTP password">
              <input
                type="password"
                value={email.smtp_password}
                onChange={(e) => setEmail({ ...email, smtp_password: e.target.value })}
                placeholder={meta.EMAIL?.settings?.smtp_password_configured ? '•••• stored' : ''}
              />
            </Field>
            <Field label="From address"><input value={email.smtp_from} onChange={(e) => setEmail({ ...email, smtp_from: e.target.value })} /></Field>
            <label className="row">
              <input type="checkbox" checked={email.smtp_use_tls} onChange={(e) => setEmail({ ...email, smtp_use_tls: e.target.checked })} />
              Use TLS
            </label>
            <button className="btn btn-primary" type="submit">Save Email (encrypt)</button>
          </form>
        </div>
      )}

      {tab === 'whatsapp' && (
        <div role="tabpanel" className="stack">
          <p className="muted">WhatsApp API credentials are encrypted at rest.</p>
          <form className="panel stack" onSubmit={saveWhatsapp} style={{ maxWidth: 640 }}>
            <label className="row">
              <input type="checkbox" checked={whatsapp.enabled} onChange={(e) => setWhatsapp({ ...whatsapp, enabled: e.target.checked })} />
              Enable WhatsApp provider
            </label>
            <Field label="API URL"><input value={whatsapp.api_url} onChange={(e) => setWhatsapp({ ...whatsapp, api_url: e.target.value })} /></Field>
            <Field label="API key">
              <input
                type="password"
                value={whatsapp.api_key}
                onChange={(e) => setWhatsapp({ ...whatsapp, api_key: e.target.value })}
                placeholder={meta.WHATSAPP?.settings?.api_key_configured ? '•••• stored' : ''}
              />
            </Field>
            <button className="btn btn-primary" type="submit">Save WhatsApp (encrypt)</button>
          </form>
        </div>
      )}

      {tab === 'sms' && (
        <div role="tabpanel" className="stack">
          <p className="muted">
            SMS remains gated by <code>NOTIFICATIONS_SMS_ENABLED</code> on the server plus the channel toggle under System Config.
          </p>
          <form className="panel stack" onSubmit={saveSms} style={{ maxWidth: 640 }}>
            <label className="row">
              <input type="checkbox" checked={sms.enabled} onChange={(e) => setSms({ ...sms, enabled: e.target.checked })} />
              Enable SMS provider credentials
            </label>
            <Field label="API URL"><input value={sms.api_url} onChange={(e) => setSms({ ...sms, api_url: e.target.value })} /></Field>
            <Field label="API key">
              <input
                type="password"
                value={sms.api_key}
                onChange={(e) => setSms({ ...sms, api_key: e.target.value })}
                placeholder={meta.SMS?.settings?.api_key_configured ? '•••• stored' : ''}
              />
            </Field>
            <button className="btn btn-primary" type="submit">Save SMS (encrypt)</button>
          </form>
        </div>
      )}

      {tab === 'overview' && (
        <div className="panel table-wrap" role="tabpanel">
          <h3>Configured providers</h3>
          <table className="data">
            <thead><tr><th>Provider</th><th>Enabled</th><th>Configured</th><th>Updated</th></tr></thead>
            <tbody>
              {Object.values(meta).map((r) => (
                <tr key={r.provider_code}>
                  <td>{r.display_name}</td>
                  <td><span className="pill">{r.enabled ? 'ON' : 'OFF'}</span></td>
                  <td>{r.configured ? 'Yes (encrypted)' : 'No'}</td>
                  <td className="muted">{r.updated_at ? new Date(r.updated_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
              {!Object.keys(meta).length && <EmptyRow cols={4} />}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
