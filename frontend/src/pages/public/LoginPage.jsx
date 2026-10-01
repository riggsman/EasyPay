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
    <div className="auth-box panel">
      <h2>Welcome back</h2>
      <p>Sign in with your username, email, or phone.</p>
      {error && <div className="alert">{error}</div>}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label>Username / Email / Phone</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>
        <div className="auth-forgot">
          <Link to="/forgot-password">Forgot password?</Link>
        </div>
        <div className="auth-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </div>
      </form>
      <div className="auth-links">
        <Link to="/register">Create Account</Link>
      </div>
      <p className="muted auth-footnote">
        Demo: abctrading / payer123 · kumba1_admin / council123 · admin / admin123
      </p>
    </div>
  )
}
