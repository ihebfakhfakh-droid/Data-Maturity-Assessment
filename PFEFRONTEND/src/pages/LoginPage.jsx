import { useState } from 'react'
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../auth/AuthProvider.jsx'
import { homePathForRole } from '../auth/roles.js'

const EMAIL_INPUT_ERROR_MESSAGE =
  'This email is invalid or is not registered in the database.'
const PASSWORD_INPUT_ERROR_MESSAGE = 'Incorrect password.'
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+$/

function isValidEmail(value) {
  return EMAIL_PATTERN.test(value.trim())
}

function SignInTitleIcon() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M12.2 14.3a4.1 4.1 0 1 0 0-8.2 4.1 4.1 0 0 0 0 8.2Z"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4.8 24.7c.9-4.1 3.7-6.4 7.4-6.4 2.2 0 4.1.8 5.4 2.2"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M20.2 15.9h6.1m0 0-2.5-2.5m2.5 2.5-2.5 2.5"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function LoginPage() {
  const auth = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  function onEmailChange(e) {
    setEmail(e.target.value)
    if (emailError) setEmailError('')
  }

  function onPasswordChange(e) {
    setPassword(e.target.value)
    if (passwordError) setPasswordError('')
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setEmailError('')
    setPasswordError('')

    const normalizedEmail = email.trim()
    if (!isValidEmail(normalizedEmail)) {
      setEmailError(EMAIL_INPUT_ERROR_MESSAGE)
      return
    }

    setLoading(true)
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: normalizedEmail, password }),
      })

      // Backend returns: { accessToken, tokenType, expiresAt, email, fullName, role }
      const token = res?.accessToken ?? res?.token ?? ''
      if (!token) throw new Error('Token missing in response')

      const role = res?.role ?? ''
      auth.setSession(token, role, rememberMe)

      // Redirect based on backend "role" (more reliable than waiting for JWT decode state)
      navigate(homePathForRole(role), { replace: true })
    } catch (err) {
      const message = err?.message ?? 'Login failed'
      if (message === EMAIL_INPUT_ERROR_MESSAGE || err?.status === 400) {
        setEmailError(message === EMAIL_INPUT_ERROR_MESSAGE ? message : EMAIL_INPUT_ERROR_MESSAGE)
        return
      }
      if (message === PASSWORD_INPUT_ERROR_MESSAGE || err?.status === 401) {
        setPasswordError(message === PASSWORD_INPUT_ERROR_MESSAGE ? message : PASSWORD_INPUT_ERROR_MESSAGE)
        return
      }
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="loginPage">
      <div className="container loginSplit">
        <section
          className="loginMarketing"
          aria-label="Assess and Improve Your Data Maturity. Unlock new value, optimize performance, and drive results."
        />

        <div className="authShell">
          <div className="loginCard">
            <div className="loginCardHeader">
              <SignInTitleIcon />
              <h1 className="loginTitle">Sign in</h1>
            </div>

            <form onSubmit={onSubmit} className="loginForm" noValidate>
              <label className="loginField">
                <span className="loginLabel">Email</span>
                <span className={`loginInputShell${emailError ? ' loginInputShellError' : ''}`}>
                  <Mail size={17} aria-hidden="true" />
                  <input
                    className="loginInput"
                    value={email}
                    onChange={onEmailChange}
                    type="email"
                    required
                    placeholder="name@company.com"
                    autoComplete="username"
                    aria-invalid={emailError ? 'true' : undefined}
                    aria-describedby={emailError ? 'login-email-error' : undefined}
                  />
                </span>
                {emailError ? (
                  <span id="login-email-error" className="fieldError">
                    {emailError}
                  </span>
                ) : null}
              </label>

              <label className="loginField">
                <span className="loginLabel">Password</span>
                <span className={`loginInputShell${passwordError ? ' loginInputShellError' : ''}`}>
                  <LockKeyhole size={17} aria-hidden="true" />
                  <input
                    className="loginInput"
                    value={password}
                    onChange={onPasswordChange}
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    aria-invalid={passwordError ? 'true' : undefined}
                    aria-describedby={passwordError ? 'login-password-error' : undefined}
                  />
                  <button
                    type="button"
                    className="loginPasswordToggle"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((visible) => !visible)}
                  >
                    {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
                  </button>
                </span>
                {passwordError ? (
                  <span id="login-password-error" className="fieldError">
                    {passwordError}
                  </span>
                ) : null}
              </label>

              {error ? <div className="alert alertError">{error}</div> : null}

              <label className="loginRemember">
                <input
                  type="checkbox"
                  className="plainCheckbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span>Remember me</span>
              </label>

              <button type="submit" className="loginSubmitButton" disabled={loading}>
                <ArrowRight size={17} aria-hidden="true" />
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

