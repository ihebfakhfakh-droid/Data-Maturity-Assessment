import { useState } from 'react'
import { apiFetch } from '../api/client.js'

export function RegisterClientPage() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      await apiFetch('/api/auth/register/client', {
        method: 'POST',
        body: JSON.stringify({ fullName, email, password }),
      })
      setSuccess('Client account created. You can sign in now.')
    } catch (err) {
      setError(err?.message ?? 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="authShell">
        <div className="card">
          <div className="cardHeader">
            <h1 className="title">Create a client account</h1>
          </div>

          <form onSubmit={onSubmit} className="form">
            <label className="field">
              <span className="label">Full name</span>
              <input
                className="input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                placeholder="e.g. Jane Doe"
                autoComplete="name"
              />
            </label>

            <label className="field">
              <span className="label">Email</span>
              <input
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                required
                autoComplete="email"
              />
            </label>

            <label className="field">
              <span className="label">Password</span>
              <input
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                required
                autoComplete="new-password"
              />
            </label>

            {error ? <div className="alert alertError">{error}</div> : null}
            {success ? <div className="alert alertSuccess">{success}</div> : null}

            <button type="submit" className="btn btnPrimary" disabled={loading}>
              {loading ? 'Creating…' : 'Create account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

