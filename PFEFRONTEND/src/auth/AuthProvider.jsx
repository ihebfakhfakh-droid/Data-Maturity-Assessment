import { createContext, useContext, useMemo, useState } from 'react'

const STORAGE_KEY = 'pfe.auth.token'
const STORAGE_ROLE_KEY = 'pfe.auth.role'

function readStored(key) {
  try {
    return localStorage.getItem(key) ?? sessionStorage.getItem(key) ?? ''
  } catch {
    return ''
  }
}

function clearStored(key) {
  try {
    localStorage.removeItem(key)
    sessionStorage.removeItem(key)
  } catch {
    // ignore storage errors
  }
}

function writeStored(key, value, remember) {
  clearStored(key)
  if (!value) return
  try {
    if (remember) localStorage.setItem(key, value)
    else sessionStorage.setItem(key, value)
  } catch {
    // ignore storage errors
  }
}

function base64UrlDecode(input) {
  const base64 = input.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  const json = atob(padded)
  return JSON.parse(json)
}

function decodeJwt(token) {
  if (!token) return null
  const parts = token.split('.')
  if (parts.length < 2) return null
  try {
    return base64UrlDecode(parts[1])
  } catch {
    return null
  }
}

function isTokenExpired(token) {
  const claims = decodeJwt(token)
  if (!claims || typeof claims.exp !== 'number') return false
  return claims.exp * 1000 <= Date.now()
}

function readInitialSession() {
  const token = readStored(STORAGE_KEY)
  const role = readStored(STORAGE_ROLE_KEY)
  if (!token) return { token: '', role: '' }
  if (isTokenExpired(token)) {
    clearStored(STORAGE_KEY)
    clearStored(STORAGE_ROLE_KEY)
    return { token: '', role: '' }
  }
  return {
    token,
    role: String(role ?? '').toUpperCase(),
  }
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const initial = readInitialSession()
  const [token, setToken] = useState(initial.token)
  const [role, setRole] = useState(initial.role)
  const claims = useMemo(() => decodeJwt(token), [token])
  const ready = true

  const value = useMemo(() => {
    const roles = claims?.roles ?? []
    const subject = claims?.sub ?? claims?.subject ?? null

    function setSession(nextToken, nextRole, remember = false) {
      const next = nextToken ?? ''
      if (next && isTokenExpired(next)) {
        clearStored(STORAGE_KEY)
        clearStored(STORAGE_ROLE_KEY)
        setToken('')
        setRole('')
        return
      }
      const normalizedRole = String(nextRole ?? '').toUpperCase()
      setToken(next)
      setRole(normalizedRole)
      writeStored(STORAGE_KEY, next, Boolean(remember))
      writeStored(STORAGE_ROLE_KEY, normalizedRole, Boolean(remember))
    }

    function logout() {
      setToken('')
      setRole('')
      clearStored(STORAGE_KEY)
      clearStored(STORAGE_ROLE_KEY)
    }

    return {
      token,
      claims,
      roles,
      role,
      subject,
      ready,
      isAuthenticated: Boolean(token) && !isTokenExpired(token),
      setToken,
      setSession,
      logout,
    }
  }, [token, claims, role, ready])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
