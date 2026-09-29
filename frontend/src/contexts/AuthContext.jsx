import { createContext, useContext, useMemo, useState, useEffect } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

function readSession() {
  const raw = localStorage.getItem('ep_session')
  return raw ? JSON.parse(raw) : null
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession)

  useEffect(() => {
    if (session) {
      localStorage.setItem('ep_session', JSON.stringify(session))
      api.setTokens(session)
    } else {
      api.clearTokens()
    }
  }, [session])

  useEffect(() => {
    function onLogout() {
      setSession(null)
    }
    function onRefresh(e) {
      setSession((prev) =>
        prev
          ? {
              ...prev,
              access_token: e.detail.access_token,
              refresh_token: e.detail.refresh_token,
              permissions: e.detail.permissions || prev.permissions,
            }
          : prev,
      )
    }
    window.addEventListener('ep:logout', onLogout)
    window.addEventListener('ep:session-refreshed', onRefresh)
    return () => {
      window.removeEventListener('ep:logout', onLogout)
      window.removeEventListener('ep:session-refreshed', onRefresh)
    }
  }, [])

  const value = useMemo(
    () => ({
      session,
      userType: session?.user_type,
      tenantId: session?.tenant_id || null,
      permissions: session?.permissions || [],
      isAuthenticated: Boolean(session?.access_token),
      async login(username, password) {
        const data = await api.login(username, password)
        setSession(data)
        return data
      },
      logout() {
        setSession(null)
      },
    }),
    [session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
