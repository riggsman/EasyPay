const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

let refreshPromise = null

function getAccess() {
  return localStorage.getItem('ep_access')
}

function getRefresh() {
  return localStorage.getItem('ep_refresh')
}

function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem('ep_access', access_token)
  if (refresh_token) localStorage.setItem('ep_refresh', refresh_token)
}

function clearTokens() {
  localStorage.removeItem('ep_access')
  localStorage.removeItem('ep_refresh')
  localStorage.removeItem('ep_session')
}

async function refreshAccessToken() {
  const refresh = getRefresh()
  if (!refresh) throw new Error('No refresh token')
  const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
  })
  if (!res.ok) {
    clearTokens()
    throw new Error('Session expired')
  }
  const data = await res.json()
  setTokens(data)
  const sessionRaw = localStorage.getItem('ep_session')
  if (sessionRaw) {
    const session = JSON.parse(sessionRaw)
    localStorage.setItem(
      'ep_session',
      JSON.stringify({
        ...session,
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        permissions: data.permissions,
      }),
    )
  }
  window.dispatchEvent(new CustomEvent('ep:session-refreshed', { detail: data }))
  return data.access_token
}

async function request(path, options = {}, retry = true) {
  const headers = {
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers || {}),
  }
  const token = getAccess()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401 && retry && getRefresh() && !path.includes('/auth/login') && !path.includes('/auth/refresh')) {
    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null
        })
      }
      await refreshPromise
      return request(path, options, false)
    } catch {
      clearTokens()
      window.dispatchEvent(new Event('ep:logout'))
    }
  }

  if (options.raw) return res

  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = { detail: text }
  }
  if (!res.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : res.statusText
    const err = new Error(message)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

async function download(path, filename) {
  const res = await request(path, { raw: true })
  if (!res.ok) throw new Error('Download failed')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function withTenant(path, tenantId) {
  if (!tenantId) return path
  const join = path.includes('?') ? '&' : '?'
  return `${path}${join}tenant_id=${encodeURIComponent(tenantId)}`
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  login: (username, password) =>
    request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }, false),
  refresh: () => refreshAccessToken(),
  register: (body) => request('/api/v1/payers/register', { method: 'POST', body: JSON.stringify(body) }, false),
  geographyChildren: (parentId) =>
    request(`/api/v1/geography/children${parentId ? `?parent_id=${parentId}` : ''}`),
  mePayer: () => request('/api/v1/payers/me'),
  operatingArea: () => request('/api/v1/payers/me/operating-area'),
  changeZone: (body) => request('/api/v1/payers/me/operating-area/change', { method: 'POST', body: JSON.stringify(body) }),
  obligations: () => request('/api/v1/obligations'),
  resolvePayment: (body) => request('/api/v1/payments/resolve', { method: 'POST', body: JSON.stringify(body) }),
  initiatePayment: (body) => request('/api/v1/payments/initiate', { method: 'POST', body: JSON.stringify(body) }),
  confirmPayment: (id) => request(`/api/v1/payments/${id}/confirm`, { method: 'POST' }),
  payments: () => request('/api/v1/payments'),
  payment: (id) => request(`/api/v1/payments/${id}`),
  receipts: () => request('/api/v1/receipts'),
  receipt: (id) => request(`/api/v1/receipts/${id}`),
  verify: (body) => request('/api/v1/public/verify', { method: 'POST', body: JSON.stringify(body) }, false),
  verifyToken: (token) => request(`/api/v1/public/verify/${token}`, {}, false),
  payerDashboard: () => request('/api/v1/dashboards/payer'),
  tenantDashboard: () => request('/api/v1/dashboards/tenant'),
  platformDashboard: () => request('/api/v1/dashboards/platform'),
  tenants: () => request('/api/v1/tenants'),
  revenueTypes: (tenantId) => request(withTenant('/api/v1/revenue-types', tenantId)),
  collectionsReport: (params = '') => request(`/api/v1/reports/collections${params}`),
  settlements: () => request('/api/v1/settlements'),
  calculateSettlement: (body, tenantId) =>
    request(withTenant('/api/v1/settlements/calculate', tenantId), { method: 'POST', body: JSON.stringify(body) }),
  approveSettlement: (id) => request(`/api/v1/settlements/${id}/approve`, { method: 'POST' }),
  processSettlement: (id) => request(`/api/v1/settlements/${id}/process`, { method: 'POST' }),
  settlementLines: (id) => request(`/api/v1/settlements/${id}/lines`),
  createObligation: (body) => request('/api/v1/obligations', { method: 'POST', body: JSON.stringify(body) }),
  createRevenueType: (body) => request('/api/v1/revenue-types', { method: 'POST', body: JSON.stringify(body) }),
  createFee: (body) => request('/api/v1/fees', { method: 'POST', body: JSON.stringify(body) }),

  opsPayers: () => request('/api/v1/ops/payers'),
  opsPayerDetail: (id) => request(`/api/v1/ops/payers/${id}/detail`),
  opsCollections: () => request('/api/v1/ops/collections'),
  opsCollectionDetail: (id) => request(`/api/v1/ops/collections/${id}/detail`),
  opsObligationDetail: (id) => request(`/api/v1/ops/obligations/${id}/detail`),
  opsSettlementDetail: (id) => request(`/api/v1/ops/settlements/${id}/detail`),
  opsDrillTransaction: (id) => request(`/api/v1/ops/drill/transaction/${id}`),
  opsAudit: (entityType) => request(`/api/v1/ops/audit${entityType ? `?entity_type=${entityType}` : ''}`),
  opsLedgerPostings: () => request('/api/v1/ops/ledger/postings'),
  opsLedgerEntries: (id) => request(`/api/v1/ops/ledger/postings/${id}/entries`),
  opsLedgerByTxn: (id) => request(`/api/v1/ops/ledger/by-transaction/${id}`),
  opsFees: () => request('/api/v1/ops/fees'),
  opsCommissions: () => request('/api/v1/ops/commissions'),
  opsCreateCommission: (body) => request('/api/v1/ops/commissions', { method: 'POST', body: JSON.stringify(body) }),
  opsStaff: () => request('/api/v1/ops/staff-users'),
  opsCreateStaff: (body) => request('/api/v1/ops/staff-users', { method: 'POST', body: JSON.stringify(body) }),
  opsRoles: () => request('/api/v1/ops/roles'),
  opsConfig: () => request('/api/v1/ops/config'),
  opsUpsertConfig: (body) => request('/api/v1/ops/config', { method: 'POST', body: JSON.stringify(body) }),
  opsReconciliation: () => request('/api/v1/ops/reconciliation'),
  opsStatement: (tenantId) => request(withTenant('/api/v1/ops/statements/tenant', tenantId)),
  opsPayerStatement: () => request('/api/v1/ops/payer-statement'),
  opsAlerts: () => request('/api/v1/ops/alerts'),
  opsSearch: (q, tenantId) => request(withTenant(`/api/v1/ops/search?q=${encodeURIComponent(q)}`, tenantId)),
  exportCollectionsCsv: (tenantId) => download(withTenant('/api/v1/ops/exports/collections.csv', tenantId), 'collections.csv'),
  exportCollectionsXlsx: (tenantId) => download(withTenant('/api/v1/ops/exports/collections.xlsx', tenantId), 'collections.xlsx'),

  clearTokens,
  setTokens,
}

export function formatMoney(amount, currency = 'XAF') {
  const n = Number(amount || 0)
  return `${n.toLocaleString('en-CM')} ${currency}`
}
