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
  const [demoOtp, setDemoOtp] = useState('')
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

  function openOtpStep(data) {
    const id = data?.challenge_id || ''
    setChallengeId(id)
    setDestinationHint(data?.destination_hint || '')
    setDemoOtp(data?.demo_otp || '')
    if (data?.demo_otp) {
      setOtp(String(data.demo_otp))
    } else {
      setOtp('')
    }
    setInfo(data?.message || 'Enter the one-time code that was sent.')
    setError('')
    // Always move to the OTP entry UI after a successful send response.
    setStep(2)
  }

  async function requestCode(e) {
    e.preventDefault()
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const data = await api.forgotPassword({ identifier: identifier.trim(), channel })
      if (!data?.challenge_id) {
        setInfo(
          `${data?.message || 'If an account matches, a one-time code was sent.'} If you do not receive a code, confirm your username/email/phone and try another channel.`,
        )
        // Still show the OTP step so the flow is visible; verify stays disabled without a challenge.
        setChallengeId('')
        setDestinationHint(data?.destination_hint || '')
        setDemoOtp('')
        setOtp('')
        setStep(2)
        return
      }
      openOtpStep(data)
    } catch (err) {
      setError(err.message || 'Could not send code')
    } finally {
      setLoading(false)
    }
  }

  async function verifyCode(e) {
    e.preventDefault()
    if (!challengeId) {
      setError('No active reset code. Go back and request a new one.')
      return
    }
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
      if (!data?.challenge_id) {
        setError('Could not resend code. Try another channel or check your details.')
        return
      }
      openOtpStep(data)
      setInfo(data.demo_otp ? data.message : 'A new code was sent.')
    } catch (err) {
      setError(err.message || 'Could not resend code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-box panel">
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
          <fieldset className="field auth-channel-fieldset">
            <legend>Send code via</legend>
            <div className="auth-channel-options">
              {CHANNELS.map((c) => {
                const enabled = !!channels[c.key]
                return (
                  <label key={c.id} className={`auth-channel-option${enabled ? '' : ' is-disabled'}`}>
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
          <div className="auth-actions">
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Sending…' : 'Send code'}
            </button>
          </div>
        </form>
      )}

      {step === 2 && (
        <form onSubmit={verifyCode} key={challengeId || 'otp-step'}>
          <p className="muted auth-step-note">
            Enter the 6-digit code sent via {channel.toLowerCase()}
            {destinationHint ? ` to ${destinationHint}` : ''}.
          </p>
          {demoOtp && (
            <div className="alert ok">
              Demo code (mock delivery): <strong className="auth-demo-otp">{demoOtp}</strong>
            </div>
          )}
          <div className="field">
            <label>One-time code</label>
            <input
              className="auth-otp-input"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="••••••"
              required
              autoFocus
            />
          </div>
          <div className="auth-actions">
            <button className="btn btn-primary" type="submit" disabled={loading || otp.length !== 6 || !challengeId}>
              {loading ? 'Verifying…' : 'Verify code'}
            </button>
            <button type="button" className="btn" onClick={resendCode} disabled={loading}>
              Resend code
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => {
                setStep(1)
                setOtp('')
                setDemoOtp('')
                setError('')
                setInfo('')
              }}
            >
              Change channel
            </button>
          </div>
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
          <div className="auth-actions">
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Saving…' : 'Update password'}
            </button>
          </div>
        </form>
      )}

      {step === 4 && (
        <div className="auth-actions">
          <div className="alert ok">{info || 'Password updated.'}</div>
          <button className="btn btn-primary" type="button" onClick={() => navigate('/login')}>
            Sign in
          </button>
        </div>
      )}

      <div className="auth-links">
        <Link to="/login">Back to sign in</Link>
      </div>
    </div>
  )
}
