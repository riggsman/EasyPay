import { io } from 'socket.io-client'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

let socket = null
let currentToken = null

function socketOrigin() {
  if (API_BASE) return API_BASE.replace(/\/$/, '')
  return window.location.origin
}

export function disconnectRealtime() {
  if (socket) {
    socket.disconnect()
    socket = null
  }
  currentToken = null
}

export function connectRealtime(accessToken, { onEvent, onConnected, onError } = {}) {
  if (!accessToken) {
    disconnectRealtime()
    return null
  }
  if (socket && currentToken === accessToken && socket.connected) {
    return socket
  }
  disconnectRealtime()
  currentToken = accessToken
  socket = io(socketOrigin(), {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    auth: { token: accessToken },
    reconnection: true,
    reconnectionAttempts: 12,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 8000,
    timeout: 20000,
  })

  socket.on('connect', () => {
    onConnected?.()
  })
  socket.on('connect_error', (err) => {
    onError?.(err?.message || 'connect_error')
  })
  socket.on('easypay:event', (message) => {
    window.dispatchEvent(new CustomEvent('ep:realtime', { detail: message }))
    onEvent?.(message)
  })
  socket.on('easypay:connected', (info) => {
    window.dispatchEvent(new CustomEvent('ep:realtime-connected', { detail: info }))
  })
  return socket
}

export function subscribeTenantFilter(tenantId) {
  if (!socket?.connected || !tenantId) return
  socket.emit('subscribe_tenant', { tenant_id: tenantId })
}
