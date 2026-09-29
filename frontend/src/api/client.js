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
    'Content-Type': 'application/json',
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
  revenueTypes: () => request('/api/v1/revenue-types'),
  collectionsReport: (params = '') => request(`/api/v1/reports/collections${params}`),
  settlements: () => request('/api/v1/settlements'),
  calculateSettlement: (body) => request('/api/v1/settlements/calculate', { method: 'POST', body: JSON.stringify(body) }),
  approveSettlement: (id) => request(`/api/v1/settlements/${id}/approve`, { method: 'POST' }),
  createObligation: (body) => request('/api/v1/obligations', { method: 'POST', body: JSON.stringify(body) }),
  clearTokens,
  setTokens,
}

export function formatMoney(amount, currency = 'XAF') {
  const n = Number(amount || 0)
  return `${n.toLocaleString('en-CM')} ${currency}`
}
