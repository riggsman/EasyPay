import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../api/client'

const CHANNELS = [
  { id: 'EMAIL', label: 'Email', key: 'email' },
  { id: 'SMS', label: 'SMS', key: 'sms' },
  { id: 'WHATSAPP', label: 'WhatsApp', key: 'whatsapp' },
]

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [identifier, setIdentifier] = useState('')
  const [channel, setChannel] = useState('EMAIL')
  const [channels, setChannels] = useState({ email: true, sms: false, whatsapp: true })
  const [challengeId, setChallengeId] = useState('')
  const [destinationHint, setDestinationHint] = useState('')
  const [otp, setOtp] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api
      .passwordResetChannels()
      .then((data) => {
        setChannels(data)
        const first = CHANNELS.find((c) => data[c.key])
        if (first) setChannel(first.id)
      })
      .catch(() => {})
  }, [])

  async function requestCode(e) {
    e.preventDefault()
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const data = await api.forgotPassword({ identifier: identifier.trim(), channel })
      setInfo(data.message)
      if (!data.challenge_id) {
        // Keep response generic (no account enumeration) while still guiding the user.
        setInfo(
          `${data.message} If you do not receive a code, confirm your username/email/phone and try another channel.`,
        )
        return
      }
      setChallengeId(data.challenge_id)
      setDestinationHint(data.destination_hint || '')
      setStep(2)
    } catch (err) {
      setError(err.message || 'Could not send code')
    } finally {
      setLoading(false)
    }
  }

  async function verifyCode(e) {
    e.preventDefault()
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const data = await api.verifyOtp({ challenge_id: challengeId, otp: otp.trim() })
      setResetToken(data.reset_token)
      setInfo(data.message)
      setStep(3)
    } catch (err) {
      setError(err.message || 'Invalid code')
    } finally {
      setLoading(false)
    }
  }

  async function submitNewPassword(e) {
    e.preventDefault()
    setError('')
    setInfo('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== passwordConfirm) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const data = await api.resetPassword({
        reset_token: resetToken,
        new_password: password,
        new_password_confirm: passwordConfirm,
      })
      setInfo(data.message || 'Password updated.')
      setStep(4)
    } catch (err) {
      setError(err.message || 'Could not reset password')
    } finally {
      setLoading(false)
    }
  }

  async function resendCode() {
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const data = await api.forgotPassword({ identifier: identifier.trim(), channel })
      if (!data.challenge_id) {
        setError('Could not resend code.')
        return
      }
      setChallengeId(data.challenge_id)
      setDestinationHint(data.destination_hint || '')
      setOtp('')
      setInfo('A new code was sent.')
    } catch (err) {
      setError(err.message || 'Could not resend code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-box panel rise">
      <h2>Forgot password</h2>
      <p>Reset your EasyPay password with a one-time code.</p>
      {error && <div className="alert">{error}</div>}
      {info && !error && step !== 4 && <div className="alert ok">{info}</div>}

      {step === 1 && (
        <form onSubmit={requestCode}>
          <div className="field">
            <label>Username / Email / Phone</label>
            <input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoComplete="username"
            />
          </div>
          <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
            <legend style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              Send code via
            </legend>
            <div style={{ display: 'grid', gap: '0.5rem' }}>
              {CHANNELS.map((c) => {
                const enabled = !!channels[c.key]
                return (
                  <label
                    key={c.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.6rem',
                      opacity: enabled ? 1 : 0.45,
                      cursor: enabled ? 'pointer' : 'not-allowed',
                    }}
                  >
                    <input
                      type="radio"
                      name="channel"
                      value={c.id}
                      checked={channel === c.id}
                      disabled={!enabled}
                      onChange={() => setChannel(c.id)}
                    />
                    <span>
                      {c.label}
                      {!enabled ? ' (unavailable)' : ''}
                    </span>
                  </label>
                )
              })}
            </div>
          </fieldset>
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', marginTop: '0.5rem' }}>
            {loading ? 'Sending…' : 'Send code'}
          </button>
        </form>
      )}

      {step === 2 && (
        <form onSubmit={verifyCode}>
          <p className="muted" style={{ marginBottom: '1rem' }}>
            Enter the 6-digit code sent via {channel.toLowerCase()}
            {destinationHint ? ` to ${destinationHint}` : ''}.
          </p>
          <div className="field">
            <label>One-time code</label>
            <input
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="••••••"
              required
              style={{ letterSpacing: '0.35em', fontSize: '1.25rem' }}
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading || otp.length !== 6} style={{ width: '100%' }}>
            {loading ? 'Verifying…' : 'Verify code'}
          </button>
          <button
            type="button"
            className="btn"
            onClick={resendCode}
            disabled={loading}
            style={{ width: '100%', marginTop: '0.75rem' }}
          >
            Resend code
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => {
              setStep(1)
              setOtp('')
              setError('')
              setInfo('')
            }}
            style={{ width: '100%', marginTop: '0.5rem' }}
          >
            Change channel
          </button>
        </form>
      )}

      {step === 3 && (
        <form onSubmit={submitNewPassword}>
          <div className="field">
            <label>New password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </div>
          <div className="field">
            <label>Confirm password</label>
            <input
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%' }}>
            {loading ? 'Saving…' : 'Update password'}
          </button>
        </form>
      )}

      {step === 4 && (
        <div>
          <div className="alert ok">{info || 'Password updated.'}</div>
          <button className="btn btn-primary" type="button" style={{ width: '100%' }} onClick={() => navigate('/login')}>
            Sign in
          </button>
        </div>
      )}

      <p style={{ marginTop: '1rem' }}>
        <Link to="/login">Back to sign in</Link>
      </p>
    </div>
  )
}
