import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'
import { connectRealtime, disconnectRealtime, subscribeTenantFilter } from '../realtime/socket'

const RealtimeContext = createContext(null)

export function RealtimeProvider({ children }) {
  const { session, isAuthenticated } = useAuth()
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    if (!isAuthenticated || !session?.access_token) {
      disconnectRealtime()
      setConnected(false)
      return undefined
    }
    connectRealtime(session.access_token, {
      onConnected: () => setConnected(true),
      onError: () => setConnected(false),
      onEvent: (message) => {
        setLastEvent(message)
        if (message?.type === 'notification.delivery') {
          const p = message.payload || {}
          const title = `${p.channel} ${p.status}`
          const body = p.event_type ? `${p.event_type} → ${p.recipient_masked || '—'}` : ''
          setToasts((prev) => [{ id: message.event_id, title, body, ts: Date.now() }, ...prev].slice(0, 6))
        }
      },
    })
    return () => {
      disconnectRealtime()
      setConnected(false)
    }
  }, [isAuthenticated, session?.access_token])

  useEffect(() => {
    const tenantFilter = localStorage.getItem('ep_tenant_filter')
    if (tenantFilter && session?.user_type === 'PLATFORM_ADMIN') {
      subscribeTenantFilter(tenantFilter)
    }
  }, [session?.user_type, connected])

  useEffect(() => {
    function onTenantFilter(e) {
      if (session?.user_type === 'PLATFORM_ADMIN' && e.detail) {
        subscribeTenantFilter(e.detail)
      }
    }
    window.addEventListener('ep:tenant-filter', onTenantFilter)
    return () => window.removeEventListener('ep:tenant-filter', onTenantFilter)
  }, [session?.user_type, connected])

  useEffect(() => {
    if (!toasts.length) return undefined
    const t = setTimeout(() => setToasts((prev) => prev.slice(0, -1)), 8000)
    return () => clearTimeout(t)
  }, [toasts])

  const value = useMemo(
    () => ({ connected, lastEvent, toasts, dismissToast: (id) => setToasts((p) => p.filter((x) => x.id !== id)) }),
    [connected, lastEvent, toasts],
  )

  return (
    <RealtimeContext.Provider value={value}>
      {children}
      {toasts.length > 0 && (
        <div className="realtime-toasts" aria-live="polite">
          {toasts.map((t) => (
            <div key={t.id} className="realtime-toast panel">
              <strong>{t.title}</strong>
              <p className="muted">{t.body}</p>
            </div>
          ))}
        </div>
      )}
    </RealtimeContext.Provider>
  )
}

export function useRealtime() {
  return useContext(RealtimeContext)
}
