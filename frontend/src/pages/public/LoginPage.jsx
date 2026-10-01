import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(username, password)
      if (data.user_type === 'PAYER') navigate('/payer')
      else if (data.user_type === 'PLATFORM_ADMIN') navigate('/platform')
      else navigate('/tenant')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-box panel rise">
      <h2>Welcome back</h2>
      <p>Sign in with your username, email, or phone.</p>
      {error && <div className="alert">{error}</div>}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label>Username / Email / Phone</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div className="field">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <p style={{ margin: '-0.35rem 0 1rem', textAlign: 'right' }}>
          <Link to="/forgot-password">Forgot password?</Link>
        </p>
        <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>
      <p style={{ marginTop: '1rem' }}>
        <Link to="/register">Create Account</Link>
      </p>
      <p className="muted" style={{ fontSize: '0.85rem' }}>
        Demo: abctrading / payer123 · kumba1_admin / council123 · admin / admin123 (wireitapp@gmail.com · 682835503)
      </p>
    </div>
  )
}
