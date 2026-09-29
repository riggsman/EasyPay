import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'
import { ChainSteps, Disclosure, EmptyRow, MoneyCells, PageHeader, PaginationBar, StatLink } from '../../components/OpsUI'

function useCtx() {
  return useOutletContext() || {}
}

function useBase() {
  const { basePath } = useCtx()
  return basePath || '/tenant'
}

function matches(q, ...parts) {
  if (!q) return true
  const s = q.toLowerCase()
  return parts.some((p) => String(p || '').toLowerCase().includes(s))
}

export function OpsDashboard({ mode = 'tenant' }) {
  const base = mode === 'platform' ? '/platform' : '/tenant'
  const { tenantFilter } = useCtx()
  const [stats, setStats] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      mode === 'platform' ? api.platformDashboard() : api.tenantDashboard(),
      api.opsAlerts(),
      api.collectionsReport(tenantFilter ? `?` : ''),
    ])
      .then(([s, a, r]) => {
        setStats(s)
        setAlerts(a)
        setReport(r)
      })
      .catch((e) => setError(e.message))
  }, [mode, tenantFilter])

  return (
    <div className="rise stack">
      <PageHeader
        title={mode === 'platform' ? 'Platform Operations' : 'Council Operations'}
        subtitle="Financial status first. Every figure drills into underlying records."
      />
      {error && <div className="alert">{error}</div>}
      <div className="stat-grid">
        <StatLink to={`${base}/reports`} label="Collections today" value={formatMoney(stats?.collections_today)} />
        <StatLink to={`${base}/transactions`} label="Transactions today" value={stats?.transactions_today ?? 0} />
        <StatLink to={`${base}/transactions`} label="Successful" value={stats?.successful_today ?? 0} />
        <StatLink to={`${base}/alerts`} label="Pending / exceptions" value={stats?.pending_today ?? alerts?.pending_transactions ?? 0} />
        <StatLink to={`${base}/settlements`} label="Settlements awaiting approval" value={alerts?.settlements_awaiting_approval ?? 0} />
        <StatLink to={`${base}/reports`} label="Gross settled" value={formatMoney(report?.gross_collections)} />
      </div>
      <div className="panel">
        <h3>Traceability path</h3>
        <ChainSteps steps={['Revenue', 'Payer', 'Obligation', 'Collection', 'Transaction', 'Fee/Commission', 'Ledger', 'Settlement']} />
      </div>
    </div>
  )
}

export function OpsAlerts() {
  const base = useBase()
  const navigate = useNavigate()
  const [alerts, setAlerts] = useState(null)
  useEffect(() => {
    api.opsAlerts().then(setAlerts).catch(() => {})
  }, [])
  useEffect(() => {
    function onRealtime(e) {
      const msg = e.detail
      if (msg?.type === 'alerts.updated') {
        const { digest: _d, ...snapshot } = msg.payload || {}
        setAlerts(snapshot)
      }
    }
    window.addEventListener('ep:realtime', onRealtime)
    return () => window.removeEventListener('ep:realtime', onRealtime)
  }, [])

  return (
    <div className="rise stack">
      <PageHeader title="Operational Alerts" subtitle="Actionable exception queues — not decoration." />
      <div className="stat-grid">
        <StatLink label="Pending transactions" value={alerts?.pending_transactions ?? 0} />
        <StatLink label="Rejected" value={alerts?.rejected_transactions ?? 0} />
        <StatLink label="Settlements awaiting approval" value={alerts?.settlements_awaiting_approval ?? 0} />
      </div>

      <div className="panel">
        <h3>Pending transactions</h3>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Reference</th><th>Amount</th><th>Status</th><th>When</th></tr></thead>
            <tbody>
              {(alerts?.items?.pending || []).map((t) => (
                <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                  <td>{t.reference}</td>
                  <td>{formatMoney(t.amount)}</td>
                  <td><span className="pill">{t.status}</span></td>
                  <td>{t.initiated_at ? new Date(t.initiated_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
              {!alerts?.items?.pending?.length && <EmptyRow cols={4} text="No pending transactions." />}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h3>Rejected transactions</h3>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Reference</th><th>Amount</th><th>Status</th><th>When</th></tr></thead>
            <tbody>
              {(alerts?.items?.rejected || []).map((t) => (
                <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                  <td>{t.reference}</td>
                  <td>{formatMoney(t.amount)}</td>
                  <td><span className="pill">{t.status}</span></td>
                  <td>{t.initiated_at ? new Date(t.initiated_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
              {!alerts?.items?.rejected?.length && <EmptyRow cols={4} text="No rejected transactions." />}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h3>Settlements awaiting approval</h3>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Reference</th><th>Net</th><th>Status</th></tr></thead>
            <tbody>
              {(alerts?.items?.settlements || []).map((s) => (
                <tr key={s.settlement_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/settlements/${s.settlement_id}`)}>
                  <td>{s.reference}</td>
                  <td>{formatMoney(s.net_amount)}</td>
                  <td><span className="pill">{s.status}</span></td>
                </tr>
              ))}
              {!alerts?.items?.settlements?.length && <EmptyRow cols={3} text="No settlements awaiting approval." />}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export function OpsSearchResults() {
  const { searchResults, basePath } = useCtx()
  const base = basePath || '/tenant'
  const navigate = useNavigate()
  const results = searchResults?.results || []

  function go(r) {
    if (r.type === 'transaction') navigate(`${base}/transactions/${r.id}`)
    else if (r.type === 'payer') navigate(`${base}/payers/${r.id}`)
    else if (r.type === 'receipt') navigate(`${base}/receipts`)
    else if (r.type === 'settlement') navigate(`${base}/settlements/${r.id}`)
  }

  return (
    <div className="rise stack">
      <PageHeader title="Search results" subtitle={searchResults?.query ? `Query: ${searchResults.query}` : 'Enter a query in the top search box'} />
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Type</th><th>Label</th><th>Status</th><th>Amount</th></tr></thead>
          <tbody>
            {results.map((r) => (
              <tr key={`${r.type}-${r.id}`} style={{ cursor: 'pointer' }} onClick={() => go(r)}>
                <td><span className="pill">{r.type}</span></td>
                <td>{r.label}{r.reference ? ` · ${r.reference}` : ''}</td>
                <td>{r.status || '—'}</td>
                <td>{r.amount != null ? formatMoney(r.amount) : '—'}</td>
              </tr>
            ))}
            {!results.length && <EmptyRow cols={4} text="No matches." />}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsPayers() {
  const base = useBase()
  const navigate = useNavigate()
  const { searchQuery, tenantFilter } = useCtx()
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  const [error, setError] = useState('')
  useEffect(() => {
    setPage(1)
  }, [searchQuery, tenantFilter])
  useEffect(() => {
    api
      .opsPayers({
        page,
        page_size: pageSize,
        q: searchQuery || undefined,
        tenant_id: tenantFilter || undefined,
      })
      .then((res) => {
        setRows(listItems(res))
        setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
      })
      .catch((e) => setError(e.message))
  }, [page, pageSize, searchQuery, tenantFilter])
  return (
    <div className="rise">
      <PageHeader title="Payers" subtitle="Tenant scope from session. Click a row for obligations → payments → receipts." />
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Name</th><th>Business</th><th>Contact</th><th>Status</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.payer_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/payers/${p.payer_id}`)}>
                <td>{p.payer_reference}</td>
                <td>{p.full_name}</td>
                <td>{p.business_name || '—'}</td>
                <td className="muted">{p.email || p.phone_number || '—'}</td>
                <td><span className="pill">{p.status}</span></td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={5} />}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          totalPages={meta.total_pages}
          total={meta.total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      </div>
    </div>
  )
}

export function OpsPayerDetail() {
  const { id } = useParams()
  const base = useBase()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.opsPayerDetail(id).then(setData).catch((e) => setError(e.message))
  }, [id])
  if (error) return <div className="alert">{error}</div>
  if (!data) return <p>Loading…</p>
  const p = data.payer
  return (
    <div className="rise stack">
      <PageHeader title={p.business_name || p.full_name} subtitle={`Ref ${p.payer_reference}`} actions={<Link className="btn btn-ghost" to={`${base}/payers`}>Back</Link>} />
      <ChainSteps steps={['Payer', 'Obligation', 'Collection', 'Transaction', 'Receipt']} active="Payer" />
      <div className="panel">
        <p>{p.email} · {p.phone_number}</p>
        <p className="muted">Current zone snapshot context is used only for new obligations/payments.</p>
      </div>
      <Disclosure title="Obligations" open>
        <table className="data">
          <thead><tr><th>Description</th><th>Amount</th><th>Balance</th><th>Status</th></tr></thead>
          <tbody>
            {data.obligations.map((o) => (
              <tr key={o.obligation_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/obligations/${o.obligation_id}`)}>
                <td>{o.description}</td>
                <td>{formatMoney(o.amount)}</td>
                <td>{formatMoney(o.balance)}</td>
                <td><span className="pill">{o.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Disclosure>
      <Disclosure title="Transactions">
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Status</th><th>Zone snapshot</th></tr></thead>
          <tbody>
            {data.transactions.map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                <td>{t.reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td><span className="pill">{t.status}</span></td>
                <td className="muted">{t.geographic_unit_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Disclosure>
      <Disclosure title="Receipts">
        <table className="data">
          <thead><tr><th>Receipt</th><th>Total</th><th>Status</th></tr></thead>
          <tbody>
            {data.receipts.map((r) => (
              <tr key={r.receipt_id}>
                <td>{r.receipt_number}</td>
                <td>{formatMoney(r.total_amount)}</td>
                <td><span className="pill">{r.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function OpsCollections() {
  const base = useBase()
  const navigate = useNavigate()
  const { tenantFilter } = useCtx()
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  useEffect(() => {
    api
      .opsCollections({ page, page_size: pageSize, tenant_id: tenantFilter || undefined })
      .then((res) => {
        setRows(listItems(res))
        setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
      })
      .catch(() => {})
  }, [page, pageSize, tenantFilter])
  return (
    <div className="rise">
      <PageHeader title="Collections" subtitle="Each collection preserves geographic and tenant snapshots." />
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Collection</th><th>Payer</th><th>Amount</th><th>Zone snapshot</th><th>Status</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.collection_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/collections/${c.collection_id}`)}>
                <td>{c.collection_id.slice(0, 14)}…</td>
                <td className="muted">{c.payer_id.slice(0, 12)}…</td>
                <td>{formatMoney(c.amount, c.currency)}</td>
                <td className="muted">{c.geographic_unit_id.slice(0, 12)}…</td>
                <td><span className="pill">{c.status}</span></td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={5} />}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          totalPages={meta.total_pages}
          total={meta.total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      </div>
    </div>
  )
}

export function OpsCollectionDetail() {
  const { id } = useParams()
  const base = useBase()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  useEffect(() => {
    api.opsCollectionDetail(id).then(setData).catch(() => {})
  }, [id])
  if (!data) return <p>Loading…</p>
  const c = data.collection
  return (
    <div className="rise stack">
      <PageHeader title="Collection detail" subtitle={c.collection_id} actions={<Link className="btn btn-ghost" to={`${base}/collections`}>Back</Link>} />
      <ChainSteps steps={['Obligation', 'Collection', 'Transaction', 'Ledger', 'Settlement']} active="Collection" />
      <div className="panel stack">
        <div><span className="muted">Amount</span><br /><strong>{formatMoney(c.amount, c.currency)}</strong></div>
        <div><span className="muted">Status</span><br /><span className="pill">{c.status}</span></div>
        <div><span className="muted">Zone snapshot</span><br />{c.geographic_unit_id}</div>
      </div>
      <Disclosure title="Linked transactions" open>
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Status</th></tr></thead>
          <tbody>
            {data.transactions.map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                <td>{t.reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td><span className="pill">{t.status}</span></td>
              </tr>
            ))}
            {!data.transactions.length && <EmptyRow cols={3} />}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function OpsObligationDetail() {
  const { id } = useParams()
  const base = useBase()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  useEffect(() => {
    api.opsObligationDetail(id).then(setData).catch(() => {})
  }, [id])
  if (!data) return <p>Loading…</p>
  const o = data.obligation
  return (
    <div className="rise stack">
      <PageHeader title={o.description || 'Obligation'} actions={<Link className="btn btn-ghost" to={`${base}/obligations`}>Back</Link>} />
      <ChainSteps steps={['Payer', 'Revenue', 'Obligation', 'Collection', 'Transaction']} active="Obligation" />
      <MoneyCells amount={o.amount} fee={0} commission={0} total={o.balance} />
      <div className="panel">
        <p>Status: <span className="pill">{o.status}</span></p>
        <p className="muted">Zone snapshot: {o.geographic_unit_id}</p>
        {data.payer && (
          <p>
            Payer:{' '}
            <button className="linkish" type="button" onClick={() => navigate(`${base}/payers/${data.payer.payer_id}`)}>
              {data.payer.name} ({data.payer.reference})
            </button>
          </p>
        )}
        {data.revenue && <p>Revenue: {data.revenue.name} ({data.revenue.code})</p>}
      </div>
      <Disclosure title="Collections" open>
        <table className="data">
          <thead><tr><th>Collection</th><th>Amount</th><th>Status</th></tr></thead>
          <tbody>
            {data.collections.map((c) => (
              <tr key={c.collection_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/collections/${c.collection_id}`)}>
                <td>{c.collection_id.slice(0, 14)}…</td>
                <td>{formatMoney(c.amount)}</td>
                <td><span className="pill">{c.status}</span></td>
              </tr>
            ))}
            {!data.collections.length && <EmptyRow cols={3} />}
          </tbody>
        </table>
      </Disclosure>
      <Disclosure title="Transactions" open>
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Status</th></tr></thead>
          <tbody>
            {data.transactions.map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                <td>{t.reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td><span className="pill">{t.status}</span></td>
              </tr>
            ))}
            {!data.transactions.length && <EmptyRow cols={3} />}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function OpsTransactions() {
  const base = useBase()
  const navigate = useNavigate()
  const { searchQuery, tenantFilter } = useCtx()
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  const [error, setError] = useState('')
  useEffect(() => {
    setPage(1)
  }, [searchQuery, tenantFilter])
  useEffect(() => {
    const statusOnly = searchQuery?.startsWith('status:') ? searchQuery.slice(7) : undefined
    api
      .payments({
        page,
        page_size: pageSize,
        status: statusOnly,
        q: statusOnly ? undefined : (searchQuery || undefined),
        tenant_id: tenantFilter || undefined,
      })
      .then((res) => {
        setRows(listItems(res))
        setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
      })
      .catch((e) => setError(e.message))
  }, [page, pageSize, searchQuery, tenantFilter])
  return (
    <div className="rise">
      <PageHeader title="Transactions" subtitle="Server-filtered list. Click a row for progressive disclosure and drill chain." />
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Status</th><th>Channel</th><th>Provider</th><th>Date</th></tr></thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                <td><strong>{t.transaction_reference}</strong></td>
                <td>{formatMoney(t.amount)}</td>
                <td><span className="pill">{t.status}</span></td>
                <td>{t.payment_channel}</td>
                <td className="muted">{t.payment_provider || '—'}</td>
                <td>{new Date(t.initiated_at).toLocaleString()}</td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={6} />}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          totalPages={meta.total_pages}
          total={meta.total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      </div>
    </div>
  )
}

export function OpsTransactionDetail() {
  const { id } = useParams()
  const base = useBase()
  const navigate = useNavigate()
  const [drill, setDrill] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.opsDrillTransaction(id).then(setDrill).catch((e) => setError(e.message))
  }, [id])
  if (error) return <div className="alert">{error}</div>
  if (!drill) return <p>Loading…</p>
  const t = drill.transaction
  return (
    <div className="rise stack">
      <PageHeader
        title={t.reference}
        subtitle="Summary → details → advanced → audit"
        actions={<Link className="btn btn-ghost" to={`${base}/transactions`}>Back</Link>}
      />
      <div className="row">
        <span className="pill">{t.status}</span>
        <span className="muted">{t.payment_channel}</span>
        <span className="muted">{t.initiated_at ? new Date(t.initiated_at).toLocaleString() : ''}</span>
      </div>
      <MoneyCells amount={t.amount} fee={t.service_fee} commission={t.commission_amount} total={t.total_amount} />
      <ChainSteps steps={drill.chain} active="transaction" />

      <div className="panel stack">
        <p>
          Payer:{' '}
          {drill.payer?.payer_id ? (
            <button className="linkish" type="button" onClick={() => navigate(`${base}/payers/${drill.payer.payer_id}`)}>
              {drill.payer.name} ({drill.payer.reference})
            </button>
          ) : '—'}
        </p>
        <p>Council: {drill.tenant?.name}</p>
        <p>Zone snapshot: {drill.geography?.name} ({drill.geography?.code})</p>
        <p>Revenue: {drill.revenue?.name || '—'}</p>
        {drill.receipt?.receipt_number && <p>Receipt: {drill.receipt.receipt_number}</p>}
      </div>

      <Disclosure title="Fee / commission calculation" open>
        <p>
          Gross {formatMoney(drill.fee_commission.service_fee ? t.amount : t.amount)} − commission{' '}
          {formatMoney(drill.fee_commission.commission_amount)} = net to council{' '}
          {formatMoney(drill.fee_commission.net_to_tenant)}. Platform service fee{' '}
          {formatMoney(drill.fee_commission.service_fee)}.
        </p>
      </Disclosure>

      <Disclosure title="State history" open>
        <div className="timeline">
          {(drill.events || []).map((e, i) => (
            <div className="item" key={i}>
              <strong>{e.to_status}</strong>
              <span className="muted">{e.note} · {e.created_at ? new Date(e.created_at).toLocaleString() : ''}</span>
            </div>
          ))}
        </div>
      </Disclosure>

      <Disclosure title="Ledger posting">
        {!drill.ledger?.posting_id && <p className="muted">No ledger posting yet.</p>}
        {!!drill.ledger?.entries?.length && (
          <table className="data">
            <thead><tr><th>Debit</th><th>Credit</th><th>Narrative</th></tr></thead>
            <tbody>
              {drill.ledger.entries.map((e, i) => (
                <tr key={i}>
                  <td>{formatMoney(e.debit)}</td>
                  <td>{formatMoney(e.credit)}</td>
                  <td>{e.narrative}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Disclosure>

      <Disclosure title="Linked records">
        <div className="row">
          {drill.obligation?.obligation_id && (
            <button className="btn btn-ghost" type="button" onClick={() => navigate(`${base}/obligations/${drill.obligation.obligation_id}`)}>
              Obligation
            </button>
          )}
          {drill.collection?.collection_id && (
            <button className="btn btn-ghost" type="button" onClick={() => navigate(`${base}/collections/${drill.collection.collection_id}`)}>
              Collection
            </button>
          )}
          {drill.settlement?.settlement_id && (
            <button className="btn btn-ghost" type="button" onClick={() => navigate(`${base}/settlements/${drill.settlement.settlement_id}`)}>
              Settlement {drill.settlement.reference}
            </button>
          )}
          {drill.receipt?.receipt_number && <Link className="btn btn-ghost" to="/verify">Verify receipt</Link>}
        </div>
      </Disclosure>

      <Disclosure title="Audit trail">
        <table className="data">
          <thead><tr><th>When</th><th>Action</th><th>Reason</th><th>Actor</th></tr></thead>
          <tbody>
            {(drill.audit || []).map((a, i) => (
              <tr key={i}>
                <td>{a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</td>
                <td><span className="pill">{a.action}</span></td>
                <td>{a.reason || '—'}</td>
                <td className="muted">{a.actor_user_id ? `${a.actor_user_id.slice(0, 10)}…` : '—'}</td>
              </tr>
            ))}
            {!drill.audit?.length && <EmptyRow cols={4} text="No audit events for this transaction." />}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function OpsLedger() {
  const base = useBase()
  const navigate = useNavigate()
  const { searchQuery, tenantFilter } = useCtx()
  const [rows, setRows] = useState([])
  const [entries, setEntries] = useState([])
  const [selected, setSelected] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  useEffect(() => {
    setPage(1)
  }, [searchQuery, tenantFilter])
  useEffect(() => {
    api
      .opsLedgerPostings({
        page,
        page_size: pageSize,
        q: searchQuery || undefined,
        tenant_id: tenantFilter || undefined,
      })
      .then((res) => {
        setRows(listItems(res))
        setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
      })
      .catch(() => {})
  }, [page, pageSize, searchQuery, tenantFilter])
  async function open(id) {
    setSelected(id)
    setEntries(await api.opsLedgerEntries(id))
  }
  return (
    <div className="rise stack">
      <PageHeader title="Ledger" subtitle="Immutable double-entry postings. Expand lines, drill to transaction." />
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Posting</th><th>Type</th><th>Transaction</th><th>Description</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.ledger_posting_id} style={{ cursor: 'pointer' }} onClick={() => open(p.ledger_posting_id)}>
                <td>{p.ledger_posting_id.slice(0, 12)}…</td>
                <td><span className="pill">{p.posting_type}</span></td>
                <td>
                  {p.transaction_id ? (
                    <button
                      className="linkish"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`${base}/transactions/${p.transaction_id}`)
                      }}
                    >
                      {p.transaction_id.slice(0, 12)}…
                    </button>
                  ) : '—'}
                </td>
                <td>{p.description}</td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={4} />}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          totalPages={meta.total_pages}
          total={meta.total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      </div>
      {selected && (
        <Disclosure title="Advanced — balanced entries" open>
          <ChainSteps steps={['Transaction', 'Fee/Commission', 'Ledger', 'Settlement']} active="Ledger" />
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
        </Disclosure>
      )}
    </div>
  )
}

export function OpsReceipts() {
  const base = useBase()
  const navigate = useNavigate()
  const { searchQuery, tenantFilter } = useCtx()
  const [rows, setRows] = useState([])
  const [selected, setSelected] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  useEffect(() => {
    setPage(1)
  }, [searchQuery, tenantFilter])
  useEffect(() => {
    api
      .receipts({
        page,
        page_size: pageSize,
        q: searchQuery || undefined,
        tenant_id: tenantFilter || undefined,
      })
      .then((res) => {
        setRows(listItems(res))
        setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
      })
      .catch(() => {})
  }, [page, pageSize, searchQuery, tenantFilter])
  return (
    <div className="rise stack">
      <PageHeader title="Receipts" subtitle="Server-filtered summary → verification details → transaction drill." />
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Receipt</th><th>Council</th><th>Revenue</th><th>Total</th><th>Status</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.receipt_id} style={{ cursor: 'pointer' }} onClick={() => setSelected(r)}>
                <td>{r.receipt_number}</td>
                <td>{r.council_name}</td>
                <td>{r.revenue_name}</td>
                <td>{formatMoney(r.total_amount, r.currency)}</td>
                <td><span className="pill">{r.status}</span></td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={5} />}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          totalPages={meta.total_pages}
          total={meta.total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      </div>
      {selected && (
        <Disclosure title={`Details — ${selected.receipt_number}`} open>
          <ChainSteps steps={['Payer', 'Transaction', 'Receipt', 'Settlement']} active="Receipt" />
          <MoneyCells amount={selected.amount} fee={selected.service_fee} commission={0} total={selected.total_amount} currency={selected.currency} />
          <p>Payer display: {selected.payer_display_name}</p>
          <p>Council: {selected.council_name}</p>
          <div className="row">
            {selected.transaction_id && (
              <button className="btn btn-ghost" type="button" onClick={() => navigate(`${base}/transactions/${selected.transaction_id}`)}>
                Drill to transaction
              </button>
            )}
            <Link className="btn btn-primary" to="/verify">Open public verification</Link>
          </div>
        </Disclosure>
      )}
    </div>
  )
}

export function OpsFees() {
  const [rows, setRows] = useState([])
  const [revenues, setRevenues] = useState([])
  const [form, setForm] = useState({ fee_type: 'FLAT', fee_value: '500', revenue_type_id: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function load() {
    const [f, r] = await Promise.all([api.opsFees(), api.revenueTypes()])
    setRows(f)
    setRevenues(r)
    if (r[0] && !form.revenue_type_id) setForm((x) => ({ ...x, revenue_type_id: r[0].revenue_type_id }))
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])
  async function create(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.createFee({
        fee_type: form.fee_type,
        fee_value: form.fee_value,
        revenue_type_id: form.revenue_type_id || null,
      })
      setMessage('Fee configuration created for current tenant')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <div className="rise stack">
      <PageHeader title="Fee Configuration" subtitle="Tenant applied from session — no tenant_id field." />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <form className="panel" onSubmit={create} style={{ maxWidth: 520 }}>
        <div className="field">
          <label>Fee type</label>
          <select value={form.fee_type} onChange={(e) => setForm({ ...form, fee_type: e.target.value })}>
            <option value="FLAT">FLAT</option>
            <option value="PERCENT">PERCENT</option>
          </select>
        </div>
        <div className="field"><label>Value</label><input required value={form.fee_value} onChange={(e) => setForm({ ...form, fee_value: e.target.value })} /></div>
        <div className="field">
          <label>Revenue type</label>
          <select value={form.revenue_type_id} onChange={(e) => setForm({ ...form, revenue_type_id: e.target.value })}>
            <option value="">Any</option>
            {revenues.map((r) => <option key={r.revenue_type_id} value={r.revenue_type_id}>{r.name}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" type="submit">Add fee</button>
      </form>
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
  const [revenues, setRevenues] = useState([])
  const [form, setForm] = useState({ commission_type: 'PERCENT', commission_value: '5', revenue_type_id: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function load() {
    const [c, r] = await Promise.all([api.opsCommissions(), api.revenueTypes()])
    setRows(c)
    setRevenues(r)
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])
  async function create(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.opsCreateCommission({
        commission_type: form.commission_type,
        commission_value: form.commission_value,
        revenue_type_id: form.revenue_type_id || null,
      })
      setMessage('Commission agreement created')
      await load()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <div className="rise stack">
      <PageHeader title="Commission Agreements" subtitle="Contractual platform commission for the current tenant." />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <form className="panel" onSubmit={create} style={{ maxWidth: 520 }}>
        <div className="field">
          <label>Type</label>
          <select value={form.commission_type} onChange={(e) => setForm({ ...form, commission_type: e.target.value })}>
            <option value="PERCENT">PERCENT</option>
            <option value="FLAT">FLAT</option>
          </select>
        </div>
        <div className="field"><label>Value</label><input required value={form.commission_value} onChange={(e) => setForm({ ...form, commission_value: e.target.value })} /></div>
        <div className="field">
          <label>Revenue type</label>
          <select value={form.revenue_type_id} onChange={(e) => setForm({ ...form, revenue_type_id: e.target.value })}>
            <option value="">Any</option>
            {revenues.map((r) => <option key={r.revenue_type_id} value={r.revenue_type_id}>{r.name}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" type="submit">Add commission</button>
      </form>
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
  const [form, setForm] = useState({ username: '', password: '', full_name: '', email: '', role_code: 'TENANT_ADMIN' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function load() {
    const [u, r] = await Promise.all([api.opsStaff(), api.opsRoles()])
    setUsers(u)
    setRoles(r)
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])
  async function create(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.opsCreateStaff(form)
      setMessage('Staff user created')
      setForm({ username: '', password: '', full_name: '', email: '', role_code: 'TENANT_ADMIN' })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <div className="rise stack">
      <PageHeader title="Users & Roles" subtitle="Access control. Tenant scope applied from session for staff." />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <form className="panel" onSubmit={create} style={{ maxWidth: 560 }}>
        <div className="field"><label>Username</label><input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
        <div className="field"><label>Password</label><input type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
        <div className="field"><label>Full name</label><input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
        <div className="field"><label>Email</label><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
        <div className="field">
          <label>Role</label>
          <select value={form.role_code} onChange={(e) => setForm({ ...form, role_code: e.target.value })}>
            {roles.map((r) => <option key={r.role_id} value={r.role_code}>{r.role_name}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" type="submit">Create staff user</button>
      </form>
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
  const [notif, setNotif] = useState(null)
  const [logPage, setLogPage] = useState({ items: [], total: 0, total_pages: 1 })
  const [form, setForm] = useState({ config_key: '', config_value: '', description: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function load() {
    setRows(await api.opsConfig())
    setNotif(await api.opsNotificationSettings())
    const log = await api.opsNotificationLog({ page: 1, page_size: 20 })
    setLogPage(log)
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])
  useEffect(() => {
    function onRealtime(e) {
      const msg = e.detail
      if (msg?.type === 'notification.delivery') {
        api.opsNotificationLog({ page: 1, page_size: 20 }).then(setLogPage).catch(() => {})
      }
    }
    window.addEventListener('ep:realtime', onRealtime)
    return () => window.removeEventListener('ep:realtime', onRealtime)
  }, [])
  async function toggleChannel(key, value) {
    setError('')
    try {
      await api.opsUpdateNotificationSettings({ [key]: value })
      setMessage('Notification channels updated')
      setNotif(await api.opsNotificationSettings())
    } catch (err) {
      setError(err.message)
    }
  }
  async function save(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.opsUpsertConfig(form)
      setMessage('Configuration saved')
      setForm({ config_key: '', config_value: '', description: '' })
      await load()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <div className="rise stack">
      <PageHeader title="System Configuration" />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      {notif && (
        <Disclosure title="Notification channels (email, SMS, WhatsApp)" open>
          <p className="muted">
            SMS requires the server env <code>NOTIFICATIONS_SMS_ENABLED=true</code> before the toggle takes effect.
          </p>
          <div className="row" style={{ gap: '1rem', flexWrap: 'wrap' }}>
            <label className="row">
              <input type="checkbox" checked={notif.email_enabled} onChange={(e) => toggleChannel('email_enabled', e.target.checked)} />
              Email
            </label>
            <label className="row">
              <input
                type="checkbox"
                checked={notif.sms_enabled}
                disabled={!notif.sms_master_switch}
                onChange={(e) => toggleChannel('sms_enabled', e.target.checked)}
              />
              SMS {notif.sms_master_switch ? '' : '(disabled on server)'}
            </label>
            <label className="row">
              <input type="checkbox" checked={notif.whatsapp_enabled} onChange={(e) => toggleChannel('whatsapp_enabled', e.target.checked)} />
              WhatsApp
            </label>
          </div>
        </Disclosure>
      )}
      <Disclosure title="Recent notification deliveries">
        <table className="data">
          <thead><tr><th>When</th><th>Channel</th><th>Event</th><th>Recipient</th><th>Status</th></tr></thead>
          <tbody>
            {listItems(logPage).map((n) => (
              <tr key={n.notification_id}>
                <td>{new Date(n.created_at).toLocaleString()}</td>
                <td>{n.channel}</td>
                <td>{n.event_type}</td>
                <td className="muted">{n.recipient || '—'}</td>
                <td><span className="pill">{n.status}</span></td>
              </tr>
            ))}
            {!listItems(logPage).length && <EmptyRow cols={5} text="No deliveries yet." />}
          </tbody>
        </table>
      </Disclosure>
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
            {!rows.length && <EmptyRow cols={3} />}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsReconciliation() {
  const base = useBase()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  useEffect(() => {
    api.opsReconciliation().then(setData).catch(() => {})
  }, [])
  return (
    <div className="rise stack">
      <PageHeader title="Reconciliation" subtitle="Exceptions: settled transactions awaiting settlement matching." />
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Status</th><th>Settled</th></tr></thead>
          <tbody>
            {(data?.exceptions || []).map((e) => (
              <tr key={e.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${e.transaction_id}`)}>
                <td>{e.reference}</td>
                <td>{formatMoney(e.amount)}</td>
                <td><span className="pill">{e.status}</span></td>
                <td>{e.settled_at ? new Date(e.settled_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {!data?.exceptions?.length && <EmptyRow cols={4} text="No open exceptions." />}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsStatements() {
  const { tenantFilter } = useCtx()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.opsStatement(tenantFilter || undefined).then(setData).catch((e) => setError(e.message))
  }, [tenantFilter])
  return (
    <div className="rise stack">
      <PageHeader title="Statements" subtitle="Tenant financial statement from settled transaction snapshots." />
      {error && <div className="alert">{error}</div>}
      {data && (
        <div className="stat-grid">
          <StatLink label="Gross" value={formatMoney(data.gross_collections)} />
          <StatLink label="Fees" value={formatMoney(data.service_fees)} />
          <StatLink label="Commissions" value={formatMoney(data.commissions)} />
        </div>
      )}
      <Disclosure title="Statement lines" open>
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
            {!data?.lines?.length && <EmptyRow cols={4} />}
          </tbody>
        </table>
      </Disclosure>
      <Disclosure title="Related settlements">
        <table className="data">
          <thead><tr><th>Reference</th><th>Net</th><th>Status</th><th>Period</th></tr></thead>
          <tbody>
            {(data?.settlements || []).map((s, i) => (
              <tr key={i}>
                <td>{s.reference}</td>
                <td>{formatMoney(s.net_amount)}</td>
                <td><span className="pill">{s.status}</span></td>
                <td className="muted">{new Date(s.period_start).toLocaleDateString()} – {new Date(s.period_end).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function OpsAudit() {
  const { searchQuery } = useCtx()
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [meta, setMeta] = useState({ total: 0, total_pages: 1 })
  const [selected, setSelected] = useState(null)
  useEffect(() => {
    setPage(1)
  }, [searchQuery])
  useEffect(() => {
    api.opsAudit({ page, page_size: pageSize, entity_type: searchQuery || undefined }).then((res) => {
      setRows(listItems(res))
      setMeta({ total: res.total ?? 0, total_pages: res.total_pages ?? 1 })
    }).catch(() => {})
  }, [page, pageSize, searchQuery])
  return (
    <div className="rise stack">
      <PageHeader title="Audit Trail" subtitle="Governance record of sensitive mutations." />
      <div className="panel table-wrap">
        <table className="data">
          <thead><tr><th>When</th><th>Entity</th><th>Action</th><th>Reason</th></tr></thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.audit_event_id} style={{ cursor: 'pointer' }} onClick={() => setSelected(a)}>
                <td>{new Date(a.created_at).toLocaleString()}</td>
                <td>{a.entity_type} · {a.entity_id.slice(0, 10)}…</td>
                <td><span className="pill">{a.action}</span></td>
                <td className="muted">{a.reason || '—'}</td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={4} />}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          totalPages={meta.total_pages}
          total={meta.total}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      </div>
      {selected && (
        <Disclosure title="Advanced audit detail" open>
          <p>Entity: {selected.entity_type} / {selected.entity_id}</p>
          <p>Actor: {selected.actor_user_id || '—'}</p>
          <p>Tenant: {selected.tenant_id || '—'}</p>
        </Disclosure>
      )}
    </div>
  )
}

export function OpsSettlements() {
  const base = useBase()
  const navigate = useNavigate()
  const { tenantFilter } = useCtx()
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function load() {
    const res = await api.settlements({ page: 1, page_size: 100 })
    setRows(listItems(res))
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
      await api.calculateSettlement(
        { period_start: start.toISOString(), period_end: end.toISOString() },
        tenantFilter || undefined,
      )
      setMessage('Settlement calculated from settled transaction snapshots')
      await load()
    } catch (e) {
      setError(e.message)
    }
  }
  return (
    <div className="rise">
      <PageHeader
        title="Settlements"
        subtitle="Gross − commission = net. Open a row for geographic line breakdown."
        actions={<button className="btn btn-primary" type="button" onClick={calculate}>Calculate (30 days)</button>}
      />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Gross</th><th>Fees</th><th>Commission</th><th>Net</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.settlement_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/settlements/${s.settlement_id}`)}>
                <td>{s.settlement_reference}</td>
                <td>{formatMoney(s.gross_amount)}</td>
                <td>{formatMoney(s.service_fees)}</td>
                <td>{formatMoney(s.commission_amount)}</td>
                <td>{formatMoney(s.net_amount)}</td>
                <td><span className="pill">{s.status}</span></td>
              </tr>
            ))}
            {!rows.length && <EmptyRow cols={6} />}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function OpsSettlementDetail() {
  const { id } = useParams()
  const base = useBase()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [payoutMethod, setPayoutMethod] = useState('MOMO')
  const [momoNumber, setMomoNumber] = useState('')
  const [bankAccount, setBankAccount] = useState('')
  const [bankName, setBankName] = useState('')
  const [bankCode, setBankCode] = useState('')
  async function load() {
    setData(await api.opsSettlementDetail(id))
  }
  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [id])
  async function approve() {
    try {
      await api.approveSettlement(id)
      setMessage('Approved')
      await load()
    } catch (e) {
      setError(e.message)
    }
  }
  async function process() {
    try {
      await api.processSettlement(id, {
        payout_method: payoutMethod,
        momo_number: payoutMethod === 'MOMO' ? momoNumber || undefined : undefined,
        bank_account_number: payoutMethod === 'BANK' ? bankAccount || undefined : undefined,
        bank_account_name: payoutMethod === 'BANK' ? bankName || undefined : undefined,
        bank_code: payoutMethod === 'BANK' ? bankCode || undefined : undefined,
      })
      setMessage(`Payout processed via Campay (${payoutMethod})`)
      await load()
    } catch (e) {
      setError(e.message)
    }
  }
  if (!data) return <p>Loading…</p>
  const s = data.settlement
  return (
    <div className="rise stack">
      <PageHeader
        title={s.reference}
        subtitle="Settlement detail with geographic lines"
        actions={<Link className="btn btn-ghost" to={`${base}/settlements`}>Back</Link>}
      />
      {error && <div className="alert">{error}</div>}
      {message && <div className="alert ok">{message}</div>}
      <div className="row"><span className="pill">{s.status}</span></div>
      <MoneyCells amount={s.gross_amount} fee={s.service_fees} commission={s.commission_amount} total={s.net_amount} />
      {s.payout_method && (
        <p className="muted">
          Payout: {s.payout_method} → {s.payout_destination || '—'} · {s.payout_status || '—'}
          {s.payout_provider_reference ? ` · Campay ${s.payout_provider_reference}` : ''}
        </p>
      )}
      <div className="row">
        {s.status === 'PENDING_APPROVAL' && <button className="btn btn-primary" type="button" onClick={approve}>Approve</button>}
      </div>
      {s.status === 'APPROVED' && (
        <Disclosure title="Client reconciliation payout (Campay)" open>
          <div className="stack" style={{ maxWidth: 480 }}>
            <div className="field">
              <label>Payout channel</label>
              <select value={payoutMethod} onChange={(e) => setPayoutMethod(e.target.value)}>
                <option value="MOMO">Mobile Money (Campay disburse)</option>
                <option value="BANK">Bank transfer (Campay bank service)</option>
              </select>
            </div>
            {payoutMethod === 'MOMO' ? (
              <div className="field">
                <label>Council MoMo number</label>
                <input value={momoNumber} onChange={(e) => setMomoNumber(e.target.value)} placeholder="Uses tenant momo_number if blank" />
              </div>
            ) : (
              <>
                <div className="field">
                  <label>Bank account number</label>
                  <input value={bankAccount} onChange={(e) => setBankAccount(e.target.value)} placeholder="Uses tenant bank account if blank" />
                </div>
                <div className="field">
                  <label>Account name</label>
                  <input value={bankName} onChange={(e) => setBankName(e.target.value)} />
                </div>
                <div className="field">
                  <label>Bank code</label>
                  <input value={bankCode} onChange={(e) => setBankCode(e.target.value)} />
                </div>
              </>
            )}
            <button className="btn btn-primary" type="button" onClick={process}>Process payout via Campay</button>
          </div>
        </Disclosure>
      )}
      <Disclosure title="Geographic settlement lines" open>
        <table className="data">
          <thead>
            <tr><th>Zone</th><th>Txns</th><th>Gross</th><th>Fees</th><th>Commission</th><th>Net</th></tr>
          </thead>
          <tbody>
            {data.lines.map((l) => (
              <tr key={l.settlement_line_id}>
                <td>{l.geographic_name || l.geographic_unit_id || '—'}</td>
                <td>{l.transaction_count}</td>
                <td>{formatMoney(l.gross_amount)}</td>
                <td>{formatMoney(l.service_fees)}</td>
                <td>{formatMoney(l.commission_amount)}</td>
                <td>{formatMoney(l.net_amount)}</td>
              </tr>
            ))}
            {!data.lines.length && <EmptyRow cols={6} />}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}

export function OpsReports() {
  const { tenantFilter } = useCtx()
  const base = useBase()
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const params = tenantFilter ? `?tenant_id=${encodeURIComponent(tenantFilter)}` : ''
    api.collectionsReport(params).then(setReport).catch((e) => setError(e.message))
  }, [tenantFilter])
  return (
    <div className="rise stack">
      <PageHeader
        title="Collections Report"
        subtitle="Aggregates use transaction location snapshots — never the payer’s current zone."
        actions={(
          <>
            <button className="btn btn-ghost" type="button" onClick={() => api.exportCollectionsCsv(tenantFilter || undefined).catch((e) => setError(e.message))}>Collections CSV</button>
            <button className="btn btn-ghost" type="button" onClick={() => api.exportSettlementsCsv(tenantFilter || undefined).catch((e) => setError(e.message))}>Settlements CSV</button>
            <button className="btn btn-ghost" type="button" onClick={() => api.exportAuditCsv(tenantFilter || undefined).catch((e) => setError(e.message))}>Audit CSV</button>
            <button className="btn btn-primary" type="button" onClick={() => api.exportCollectionsXlsx(tenantFilter || undefined).catch((e) => setError(e.message))}>Collections Excel</button>
          </>
        )}
      />
      {error && <div className="alert">{error}</div>}
      {report && (
        <div className="stat-grid">
          <StatLink label="Gross" value={formatMoney(report.gross_collections)} />
          <StatLink label="Fees" value={formatMoney(report.service_fees)} />
          <StatLink label="Commission" value={formatMoney(report.commission)} />
          <StatLink label="Net" value={formatMoney(report.net_settlement)} />
        </div>
      )}
      <Disclosure title="Underlying transactions" open>
        <table className="data">
          <thead><tr><th>Reference</th><th>Amount</th><th>Geo snapshot</th><th>Settled</th></tr></thead>
          <tbody>
            {(report?.transactions || []).map((t) => (
              <tr key={t.transaction_id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${base}/transactions/${t.transaction_id}`)}>
                <td>{t.reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td className="muted">{t.geographic_unit_id}</td>
                <td>{t.settled_at ? new Date(t.settled_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {!report?.transactions?.length && <EmptyRow cols={4} />}
          </tbody>
        </table>
      </Disclosure>
    </div>
  )
}
