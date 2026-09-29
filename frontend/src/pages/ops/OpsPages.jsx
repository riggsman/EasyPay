import { useEffect, useMemo, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'

function useSearch() {
  const ctx = useOutletContext() || {}
  return (ctx.searchQuery || '').trim().toLowerCase()
}

function matches(q, ...parts) {
  if (!q) return true
  return parts.some((p) => String(p || '').toLowerCase().includes(q))
}

export function OpsDashboard({ mode = 'tenant' }) {
  const [stats, setStats] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const base = mode === 'platform' ? '/platform' : '/tenant'

  useEffect(() => {
    Promise.all([
      mode === 'platform' ? api.platformDashboard() : api.tenantDashboard(),
      api.opsAlerts(),
      api.collectionsReport(),
    ])
      .then(([s, a, r]) => {
        setStats(s)
        setAlerts(a)
        setReport(r)
      })
      .catch((e) => setError(e.message))
  }, [mode])

  return (
    <div className="rise stack">
      <div>
        <h2>{mode === 'platform' ? 'Platform Operations' : 'Council Operations'}</h2>
        <p className="muted">Financial status first. Every figure drills into underlying records.</p>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="stat-grid">
        <Link className="panel stat drill" to={`${base}/reports`}>
          <span className="muted">Collections today</span>
          <strong>{formatMoney(stats?.collections_today)}</strong>
        </Link>
        <Link className="panel stat drill" to={`${base}/transactions`}>
          <span className="muted">Transactions today</span>
          <strong>{stats?.transactions_today ?? 0}</strong>
        </Link>
        <Link className="panel stat drill" to={`${base}/transactions`}>
          <span className="muted">Successful</span>
          <strong>{stats?.successful_today ?? 0}</strong>
        </Link>
        <Link className="panel stat drill" to={`${base}/alerts`}>
          <span className="muted">Pending</span>
          <strong>{stats?.pending_today ?? alerts?.pending_transactions ?? 0}</strong>
        </Link>
        <Link className="panel stat drill" to={`${base}/settlements`}>
          <span className="muted">Settlements awaiting approval</span>
          <strong>{alerts?.settlements_awaiting_approval ?? 0}</strong>
        </Link>
        <Link className="panel stat drill" to={`${base}/reports`}>
          <span className="muted">Gross (settled)</span>
          <strong>{formatMoney(report?.gross_collections)}</strong>
        </Link>
      </div>
      <div className="panel">
        <h3>Traceability path</h3>
        <p className="muted">Collection → Revenue → Payer → Obligation → Transaction → Fee/Commission → Ledger → Settlement</p>
      </div>
    </div>
  )
}

export function OpsAlerts() {
  const [alerts, setAlerts] = useState(null)
  useEffect(() => {
    api.opsAlerts().then(setAlerts).catch(() => {})
  }, [])
  return (
    <div className="rise stack">
      <h2>Operational Alerts</h2>
      <div className="stat-grid">
        <div className="panel stat"><span className="muted">Pending transactions</span><strong>{alerts?.pending_transactions ?? 0}</strong></div>
        <div className="panel stat"><span className="muted">Rejected</span><strong>{alerts?.rejected_transactions ?? 0}</strong></div>
        <div className="panel stat"><span className="muted">Settlements awaiting approval</span><strong>{alerts?.settlements_awaiting_approval ?? 0}</strong></div>
      </div>
    </div>
  )
}

export function OpsPayers() {
  const q = useSearch()
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    api.opsPayers().then(setRows).catch((e) => setError(e.message))
  }, [])
  const filtered = useMemo(
    () => rows.filter((r) => matches(q, r.payer_reference, r.full_name, r.business_name, r.email)),
    [rows, q],
  )
  return (
    <div className="rise">
      <h2>Payers</h2>
      <p className="muted">Tenant scope applied from session. Zone shown is current operating area only.</p>
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Name</th><th>Business</th><th>Contact</th><th>Status</th></tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.payer_id}>
                <td>{p.payer_reference}</td>
                <td>{p.full_name}</td>
                <td>{p.business_name || '—'}</td>
                <td className="muted">{p.email || p.phone_number || '—'}</td>
                <td><span className="pill">{p.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsCollections() {
  const q = useSearch()
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.opsCollections().then(setRows).catch(() => {})
  }, [])
  const filtered = rows.filter((r) => matches(q, r.collection_id, r.payer_id, r.obligation_id))
  return (
    <div className="rise">
      <h2>Collections</h2>
      <p className="muted">Each collection preserves geographic and tenant snapshots from creation time.</p>
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Collection</th><th>Payer</th><th>Amount</th><th>Zone snapshot</th><th>Status</th></tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.collection_id}>
                <td>{c.collection_id.slice(0, 14)}…</td>
                <td className="muted">{c.payer_id.slice(0, 12)}…</td>
                <td>{formatMoney(c.amount, c.currency)}</td>
                <td className="muted">{c.geographic_unit_id.slice(0, 12)}…</td>
                <td><span className="pill">{c.status}</span></td>
              </tr>
            ))}
            {!filtered.length && <tr><td colSpan={5} className="muted">No collections yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsTransactions() {
  const q = useSearch()
  const [rows, setRows] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [ledger, setLedger] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.payments().then(setRows).catch((e) => setError(e.message))
  }, [])

  async function openDetail(id) {
    setSelected(id)
    setDetail(null)
    setLedger(null)
    try {
      const d = await api.payment(id)
      setDetail(d)
      const l = await api.opsLedgerByTxn(id)
      setLedger(l)
    } catch (e) {
      setError(e.message)
    }
  }

  const filtered = rows.filter((t) => matches(q, t.transaction_reference, t.transaction_id, t.status, t.payment_channel))

  return (
    <div className="rise stack">
      <div>
        <h2>Transactions</h2>
        <p className="muted">Summary first. Expand fee, commission, ledger, and state history.</p>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Amount</th><th>Status</th><th>Channel</th><th>Date</th></tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => openDetail(t.transaction_id)}>
                <td><strong>{t.transaction_reference}</strong></td>
                <td>{formatMoney(t.amount)}</td>
                <td><span className="pill">{t.status}</span></td>
                <td>{t.payment_channel}</td>
                <td>{new Date(t.initiated_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && detail && (
        <div className="panel stack">
          <div className="app-top">
            <h3>{detail.transaction_reference}</h3>
            <span className="pill">{detail.status}</span>
          </div>
          <div className="stat-grid">
            <div className="stat"><span className="muted">Amount</span><strong>{formatMoney(detail.amount)}</strong></div>
            <div className="stat"><span className="muted">Service fee</span><strong>{formatMoney(detail.service_fee)}</strong></div>
            <div className="stat"><span className="muted">Commission</span><strong>{formatMoney(detail.commission_amount)}</strong></div>
            <div className="stat"><span className="muted">Total paid</span><strong>{formatMoney(detail.total_amount)}</strong></div>
          </div>
          <p><span className="muted">Payer</span> · {detail.payer_id}</p>
          <p><span className="muted">Channel</span> · {detail.payment_channel}</p>
          <p><span className="muted">Zone snapshot (immutable)</span> · {detail.transaction_geographic_unit_id}</p>
          {detail.receipt_number && <p><span className="muted">Receipt</span> · {detail.receipt_number}</p>}

          <details className="details-block" open>
            <summary>State history</summary>
            <div className="timeline" style={{ marginTop: '0.75rem' }}>
              {(detail.events || []).map((e, i) => (
                <div className="item" key={i}>
                  <strong>{e.to_status}</strong>
                  <span className="muted">{e.note} · {new Date(e.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </details>
          <details className="details-block">
            <summary>Fee / commission calculation</summary>
            <p style={{ marginTop: '0.75rem' }}>
              Gross {formatMoney(detail.amount)} − commission {formatMoney(detail.commission_amount)} =
              net council {formatMoney(Number(detail.amount) - Number(detail.commission_amount))}.
              Platform service fee {formatMoney(detail.service_fee)}.
            </p>
          </details>
          <details className="details-block">
            <summary>Ledger posting</summary>
            {!ledger?.posting && <p className="muted" style={{ marginTop: '0.75rem' }}>No ledger posting yet.</p>}
            {ledger?.entries?.length > 0 && (
              <div className="table-wrap" style={{ marginTop: '0.75rem' }}>
                <table className="data">
                  <thead><tr><th>Account</th><th>Debit</th><th>Credit</th><th>Narrative</th></tr></thead>
                  <tbody>
                    {ledger.entries.map((e) => (
                      <tr key={e.ledger_entry_id}>
                        <td>{e.account_code} · {e.account_name}</td>
                        <td>{formatMoney(e.debit)}</td>
                        <td>{formatMoney(e.credit)}</td>
                        <td className="muted">{e.narrative}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </details>
        </div>
      )}
    </div>
  )
}

export function OpsLedger() {
  const [rows, setRows] = useState([])
  const [entries, setEntries] = useState([])
  const [selected, setSelected] = useState(null)
  useEffect(() => {
    api.opsLedgerPostings().then(setRows).catch(() => {})
  }, [])
  async function open(id) {
    setSelected(id)
    setEntries(await api.opsLedgerEntries(id))
  }
  return (
    <div className="rise stack">
      <h2>Ledger</h2>
      <p className="muted">Immutable double-entry postings. Drill into balanced debit/credit lines.</p>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Posting</th><th>Type</th><th>Transaction</th><th>Description</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.ledger_posting_id} style={{ cursor: 'pointer' }} onClick={() => open(p.ledger_posting_id)}>
                <td>{p.ledger_posting_id.slice(0, 12)}…</td>
                <td><span className="pill">{p.posting_type}</span></td>
                <td className="muted">{p.transaction_id ? `${p.transaction_id.slice(0, 12)}…` : '—'}</td>
                <td>{p.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected && (
        <div className="panel table-wrap">
          <h3>Entries</h3>
          <table className="data">
            <thead><tr><th>Debit</th><th>Credit</th><th>Narrative</th></tr></thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.ledger_entry_id}>
                  <td>{formatMoney(e.debit)}</td>
                  <td>{formatMoney(e.credit)}</td>
                  <td>{e.narrative}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function OpsReceipts() {
  const q = useSearch()
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.receipts().then(setRows).catch(() => {})
  }, [])
  const filtered = rows.filter((r) => matches(q, r.receipt_number, r.council_name, r.revenue_name, r.payer_display_name))
  return (
    <div className="rise">
      <h2>Receipts</h2>
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Receipt</th><th>Council</th><th>Revenue</th><th>Total</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.receipt_id}>
                <td>{r.receipt_number}</td>
                <td>{r.council_name}</td>
                <td>{r.revenue_name}</td>
                <td>{formatMoney(r.total_amount, r.currency)}</td>
                <td><span className="pill">{r.status}</span></td>
                <td><Link to="/verify">Verify</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsFees() {
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.opsFees().then(setRows).catch(() => {})
  }, [])
  return (
    <div className="rise">
      <h2>Fee Configuration</h2>
      <p className="muted">Tenant-scoped. Values used by payment context resolver.</p>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Type</th><th>Value</th><th>Currency</th><th>Status</th></tr></thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.fee_configuration_id}>
                <td>{f.fee_type}</td>
                <td>{f.fee_value}</td>
                <td>{f.currency}</td>
                <td><span className="pill">{f.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsCommissions() {
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.opsCommissions().then(setRows).catch(() => {})
  }, [])
  return (
    <div className="rise">
      <h2>Commission Agreements</h2>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Type</th><th>Value</th><th>Status</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.commission_agreement_id}>
                <td>{c.commission_type}</td>
                <td>{c.commission_value}</td>
                <td><span className="pill">{c.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsUsersRoles() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  useEffect(() => {
    Promise.all([api.opsStaff(), api.opsRoles()]).then(([u, r]) => {
      setUsers(u)
      setRoles(r)
    }).catch(() => {})
  }, [])
  return (
    <div className="rise stack">
      <h2>Users & Roles</h2>
      <div className="panel table-wrap">
        <h3>Staff users</h3>
        <table className="data">
          <thead><tr><th>Username</th><th>Name</th><th>Type</th><th>Active</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td>{u.username}</td>
                <td>{u.full_name}</td>
                <td>{u.user_type}</td>
                <td>{u.is_active ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel table-wrap">
        <h3>Roles</h3>
        <table className="data">
          <thead><tr><th>Code</th><th>Name</th><th>Scope</th></tr></thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.role_id}>
                <td>{r.role_code}</td>
                <td>{r.role_name}</td>
                <td>{r.scope}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsConfig() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState({ config_key: '', config_value: '', description: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function load() {
    setRows(await api.opsConfig())
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])
  async function save(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.opsUpsertConfig(form)
      setMessage('Configuration saved for current tenant/platform context')
      setForm({ config_key: '', config_value: '', description: '' })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <div className="rise stack">
      <h2>System Configuration</h2>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <form className="panel" onSubmit={save} style={{ maxWidth: 560 }}>
        <div className="field"><label>Key</label><input required value={form.config_key} onChange={(e) => setForm({ ...form, config_key: e.target.value })} /></div>
        <div className="field"><label>Value</label><input required value={form.config_value} onChange={(e) => setForm({ ...form, config_value: e.target.value })} /></div>
        <div className="field"><label>Description</label><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
        <button className="btn btn-primary" type="submit">Save</button>
      </form>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Key</th><th>Value</th><th>Description</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.config_id}>
                <td>{r.config_key}</td>
                <td>{r.config_value}</td>
                <td className="muted">{r.description}</td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={3} className="muted">No configuration rows yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsReconciliation() {
  const [data, setData] = useState(null)
  useEffect(() => {
    api.opsReconciliation().then(setData).catch(() => {})
  }, [])
  return (
    <div className="rise stack">
      <h2>Reconciliation</h2>
      <p className="muted">Exceptions surface settled transactions awaiting settlement matching.</p>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Status</th><th>Settled</th></tr></thead>
          <tbody>
            {(data?.exceptions || []).map((e) => (
              <tr key={e.transaction_id}>
                <td>{e.reference}</td>
                <td>{formatMoney(e.amount)}</td>
                <td><span className="pill">{e.status}</span></td>
                <td>{e.settled_at ? new Date(e.settled_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {!data?.exceptions?.length && <tr><td colSpan={4} className="muted">No open exceptions.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsStatements() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.opsStatement().then(setData).catch((e) => setError(e.message))
  }, [])
  return (
    <div className="rise stack">
      <h2>Tenant Statement</h2>
      {error && <div className="alert">{error}</div>}
      {data && (
        <div className="stat-grid">
          <div className="panel stat"><span className="muted">Gross</span><strong>{formatMoney(data.gross_collections)}</strong></div>
          <div className="panel stat"><span className="muted">Fees</span><strong>{formatMoney(data.service_fees)}</strong></div>
          <div className="panel stat"><span className="muted">Commissions</span><strong>{formatMoney(data.commissions)}</strong></div>
        </div>
      )}
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Date</th><th>Description</th><th>Credit</th></tr></thead>
          <tbody>
            {(data?.lines || []).map((l, i) => (
              <tr key={i}>
                <td>{l.reference}</td>
                <td>{l.date ? new Date(l.date).toLocaleDateString() : '—'}</td>
                <td>{l.description}</td>
                <td>{formatMoney(l.credit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsAudit() {
  const q = useSearch()
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.opsAudit().then(setRows).catch(() => {})
  }, [])
  const filtered = rows.filter((r) => matches(q, r.entity_type, r.entity_id, r.action, r.reason))
  return (
    <div className="rise">
      <h2>Audit Trail</h2>
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>When</th><th>Entity</th><th>Action</th><th>Reason</th></tr></thead>
          <tbody>
            {filtered.map((a) => (
              <tr key={a.audit_event_id}>
                <td>{new Date(a.created_at).toLocaleString()}</td>
                <td>{a.entity_type} · {a.entity_id.slice(0, 10)}…</td>
                <td><span className="pill">{a.action}</span></td>
                <td className="muted">{a.reason || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsSettlements() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function load() {
    setRows(await api.settlements())
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])
  async function calculate() {
    setError('')
    setMessage('')
    try {
      const end = new Date()
      const start = new Date()
      start.setDate(end.getDate() - 30)
      await api.calculateSettlement({ period_start: start.toISOString(), period_end: end.toISOString() })
      setMessage('Settlement calculated from settled transaction snapshots')
      await load()
    } catch (e) {
      setError(e.message)
    }
  }
  async function approve(id) {
    try {
      await api.approveSettlement(id)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }
  async function process(id) {
    try {
      await api.processSettlement(id)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }
  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Settlements</h2>
          <p className="muted">Gross − commission = net. Drill lines use geographic snapshots.</p>
        </div>
        <button className="btn btn-primary" type="button" onClick={calculate}>Calculate (30 days)</button>
      </div>
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Gross</th><th>Fees</th><th>Commission</th><th>Net</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.settlement_id}>
                <td>{s.settlement_reference}</td>
                <td>{formatMoney(s.gross_amount)}</td>
                <td>{formatMoney(s.service_fees)}</td>
                <td>{formatMoney(s.commission_amount)}</td>
                <td>{formatMoney(s.net_amount)}</td>
                <td><span className="pill">{s.status}</span></td>
                <td className="row">
                  {s.status === 'PENDING_APPROVAL' && (
                    <button className="btn btn-ghost" type="button" onClick={() => approve(s.settlement_id)}>Approve</button>
                  )}
                  {s.status === 'APPROVED' && (
                    <button className="btn btn-ghost" type="button" onClick={() => process(s.settlement_id)}>Process</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsReports() {
  const [report, setReport] = useState(null)
  useEffect(() => {
    api.collectionsReport().then(setReport).catch(() => {})
  }, [])
  return (
    <div className="rise stack">
      <h2>Collections Report</h2>
      <p className="muted">Aggregates use transaction location snapshots — never the payer’s current zone.</p>
      {report && (
        <div className="stat-grid">
          <div className="panel stat"><span className="muted">Gross</span><strong>{formatMoney(report.gross_collections)}</strong></div>
          <div className="panel stat"><span className="muted">Fees</span><strong>{formatMoney(report.service_fees)}</strong></div>
          <div className="panel stat"><span className="muted">Commission</span><strong>{formatMoney(report.commission)}</strong></div>
          <div className="panel stat"><span className="muted">Net</span><strong>{formatMoney(report.net_settlement)}</strong></div>
        </div>
      )}
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Geo snapshot</th><th>Settled</th></tr></thead>
          <tbody>
            {(report?.transactions || []).map((t) => (
              <tr key={t.transaction_id}>
                <td>{t.reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td className="muted">{t.geographic_unit_id}</td>
                <td>{t.settled_at ? new Date(t.settled_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
