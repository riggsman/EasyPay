import { createContext, useContext, useMemo, useState, useEffect } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    const raw = localStorage.getItem('ep_session')
    return raw ? JSON.parse(raw) : null
  })

  useEffect(() => {
    if (session) {
      localStorage.setItem('ep_session', JSON.stringify(session))
      localStorage.setItem('ep_access', session.access_token)
      localStorage.setItem('ep_refresh', session.refresh_token)
    } else {
      localStorage.removeItem('ep_session')
      localStorage.removeItem('ep_access')
      localStorage.removeItem('ep_refresh')
    }
  }, [session])

  const value = useMemo(
    () => ({
      session,
      userType: session?.user_type,
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
