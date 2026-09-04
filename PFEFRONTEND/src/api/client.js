const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').trim()

function joinUrl(base, path) {
  if (!base) return path
  const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

async function readErrorMessage(res) {
  const fallback = `API ${res.status} ${res.statusText}`
  const contentType = res.headers.get('content-type') ?? ''

  if (contentType.includes('application/json') || contentType.includes('application/problem+json')) {
    const body = await res.json().catch(() => null)
    if (!body) return fallback
    if (typeof body.message === 'string' && body.message.trim()) return body.message
    if (typeof body.detail === 'string' && body.detail.trim()) return body.detail
    if (typeof body.error === 'string' && body.error.trim()) return body.error
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0]
      if (typeof first === 'string') return first
      if (first?.msg) return String(first.msg)
    }
    return fallback
  }

  const text = await res.text().catch(() => '')
  // Backend may return JSON even when Content-Type is missing/wrong.
  if (text) {
    try {
      const body = JSON.parse(text)
      const message = body?.message ?? body?.detail ?? body?.error
      if (message) return String(message)
    } catch {
      // keep text fallback
    }
    return `${fallback} - ${text}`
  }
  return fallback
}

async function createApiError(res) {
  const error = new Error(await readErrorMessage(res))
  error.status = res.status
  return error
}

/**
 * Fetch helper for backend endpoints.
 * - In dev: keep `VITE_API_URL` empty and call `/api/...` (Vite proxy will forward to Spring Boot).
 * - In prod: set `VITE_API_URL` to your backend origin (e.g. https://api.example.com) and keep paths like `/api/...`.
 */
export async function apiFetch(path, options) {
  const url = joinUrl(API_BASE_URL, path)
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })

  if (!res.ok) {
    throw await createApiError(res)
  }

  if (res.status === 204 || res.status === 205) return null

  const contentType = res.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) return res.json()
  return res.text()
}

/**
 * Fetch helper for binary responses (PDF, etc.).
 * Returns `{ blob, filename }` and never downloads empty/invalid payloads.
 */
export async function apiFetchBlob(path, options) {
  const url = joinUrl(API_BASE_URL, path)
  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options?.headers ?? {}),
    },
  })

  if (!res.ok) {
    throw await createApiError(res)
  }

  const blob = await res.blob()
  if (!blob || blob.size === 0) {
    throw new Error('The received file is empty.')
  }

  const contentType = (res.headers.get('content-type') ?? blob.type ?? '').toLowerCase()
  if (contentType && !contentType.includes('pdf') && !contentType.includes('octet-stream')) {
    throw new Error('The server response is not a PDF file.')
  }

  const header = new Uint8Array(await blob.slice(0, 4).arrayBuffer())
  const isPdf =
    header.length >= 4 &&
    header[0] === 0x25 &&
    header[1] === 0x50 &&
    header[2] === 0x44 &&
    header[3] === 0x46
  if (!isPdf) {
    throw new Error('The received PDF file is invalid.')
  }

  const disposition = res.headers.get('content-disposition') ?? ''
  const filenameMatch =
    /filename\*=UTF-8''([^;]+)|filename="([^"]+)"|filename=([^;]+)/i.exec(disposition)
  const rawName = filenameMatch?.[1] || filenameMatch?.[2] || filenameMatch?.[3]
  const filename = rawName ? decodeURIComponent(rawName.trim()) : 'recommendations-report.pdf'

  return { blob, filename }
}

/**
 * Fetch helper for multipart/form-data uploads.
 * - Do NOT set Content-Type manually (browser sets boundary).
 */
export async function apiFetchFormData(path, { method = 'POST', headers = {}, body }) {
  const url = joinUrl(API_BASE_URL, path)
  const res = await fetch(url, {
    method,
    headers,
    body,
  })

  if (!res.ok) {
    throw await createApiError(res)
  }

  if (res.status === 204 || res.status === 205) return null
  const contentType = res.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) return res.json()
  return res.text()
}

