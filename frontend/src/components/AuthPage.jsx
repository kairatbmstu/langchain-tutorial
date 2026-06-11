import React, { useState, useEffect, useRef } from 'react'

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [captcha, setCaptcha] = useState(null)
  const [captchaAnswer, setCaptchaAnswer] = useState('')
  const [error, setError] = useState('')
  const googleBtnRef = useRef(null)

  const loadCaptcha = async () => {
    try {
      const res = await fetch('/api/captcha')
      const data = await res.json()
      setCaptcha(data)
      setCaptchaAnswer('')
    } catch { setError('Failed to load captcha') }
  }

  const handleModeSwitch = () => {
    setMode((m) => (m === 'login' ? 'register' : 'login'))
    setError('')
    if (mode === 'login') loadCaptcha()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (mode === 'register') {
      if (!captcha) { setError('Loading captcha...'); return }
      if (!captchaAnswer.trim()) { setError('Please answer the captcha'); return }

      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, captcha_id: captcha.captcha_id, captcha_answer: parseInt(captchaAnswer) }),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Registration failed')
        loadCaptcha()
        return
      }
      const data = await res.json()
      onAuth(data.token, data.user_id, data.email)
    } else {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Login failed')
        return
      }
      const data = await res.json()
      onAuth(data.token, data.user_id, data.email)
    }
  }

  const handleGoogleCredential = async (response) => {
    try {
      const res = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Google sign-in failed')
        return
      }
      const data = await res.json()
      onAuth(data.token, data.user_id, data.email)
    } catch {
      setError('Google sign-in failed')
    }
  }

  useEffect(() => {
    if (mode === 'register') loadCaptcha()
  }, [mode])

  useEffect(() => {
    if (window.google && googleBtnRef.current && googleBtnRef.current.children.length === 0) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
        callback: handleGoogleCredential,
      })
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'outline',
        size: 'large',
        width: '100%',
      })
    }
  }, [])

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>LlamaChat</h1>
        <h2>{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>

        <form onSubmit={handleSubmit}>
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />

          {mode === 'register' && captcha && (
            <div className="captcha-box">
              <p className="captcha-question">{captcha.question}</p>
              <input
                type="number"
                placeholder="Your answer"
                value={captchaAnswer}
                onChange={(e) => setCaptchaAnswer(e.target.value)}
                required
              />
            </div>
          )}

          {error && <p className="auth-error">{error}</p>}

          <button type="submit">{mode === 'login' ? 'Sign In' : 'Create Account'}</button>
        </form>

        <div className="auth-divider"><span>or</span></div>

        <div ref={googleBtnRef} className="google-btn-container"></div>

        <p className="auth-switch">
          {mode === 'login' ? (
            <>Don't have an account? <button className="link" onClick={handleModeSwitch}>Register</button></>
          ) : (
            <>Already have an account? <button className="link" onClick={handleModeSwitch}>Sign In</button></>
          )}
        </p>
      </div>
    </div>
  )
}
