const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }
  const token = localStorage.getItem('ep_access')
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
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
  login: (username, password) => request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  register: (body) => request('/api/v1/payers/register', { method: 'POST', body: JSON.stringify(body) }),
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
  verify: (body) => request('/api/v1/public/verify', { method: 'POST', body: JSON.stringify(body) }),
  verifyToken: (token) => request(`/api/v1/public/verify/${token}`),
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
}

export function formatMoney(amount, currency = 'XAF') {
  const n = Number(amount || 0)
  return `${n.toLocaleString('en-CM')} ${currency}`
}
