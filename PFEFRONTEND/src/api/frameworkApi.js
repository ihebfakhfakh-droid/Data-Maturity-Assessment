import { apiFetch } from './client.js'
import {
  DEFAULT_FRAMEWORK_OPTIONS,
  frameworkOptionsFromResponse,
  uniqueFrameworkOptions,
} from '../pages/admin/frameworkUtils.js'

/** Built-in evaluation frameworks (enum on the backend). Not loaded from maturity-frameworks. */
export const BUILT_IN_FRAMEWORK_OPTIONS = DEFAULT_FRAMEWORK_OPTIONS.map((option) => ({
  ...option,
  builtIn: true,
}))

export { DEFAULT_FRAMEWORK_OPTIONS }

export const MATURITY_FRAMEWORKS_PATH = '/api/admin/maturity-frameworks'

export const DOMAIN_SCORING_METHODS = [
  { value: 'DOMAIN_MINIMUM', label: 'Domain minimum' },
  { value: 'DOMAIN_AVERAGE', label: 'Domain average' },
]

export const FRAMEWORK_SCORE_SCALES = [
  { value: 'ZERO_TO_FIVE', label: '0 – 5' },
  { value: 'ONE_TO_FIVE', label: '1 – 5' },
]

/**
 * List admin-defined maturity frameworks.
 * Requires ADMIN role on the backend.
 */
export function listMaturityFrameworks(token, { signal } = {}) {
  return apiFetch(MATURITY_FRAMEWORKS_PATH, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
}

/**
 * Create an admin-defined maturity framework.
 * Body must match CreateMaturityFrameworkRequest.
 */
export function createMaturityFramework(token, body, { signal } = {}) {
  invalidateFrameworkCatalogCache()
  return apiFetch(MATURITY_FRAMEWORKS_PATH, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    signal,
  })
}

function isForbiddenError(error) {
  return Number(error?.status) === 403 || String(error?.message ?? '').includes('403')
}

const CATALOG_CACHE_TTL_MS = 30_000
/** @type {Map<string, { expiresAt: number, result: Awaited<ReturnType<typeof loadFrameworkCatalogUncached>> }>} */
const catalogCache = new Map()
/** @type {Map<string, Promise<Awaited<ReturnType<typeof loadFrameworkCatalogUncached>>>>} */
const catalogInflight = new Map()

export function invalidateFrameworkCatalogCache() {
  catalogCache.clear()
  catalogInflight.clear()
}

async function loadFrameworkCatalogUncached(token, { signal, includeBuiltIn = true } = {}) {
  const builtIn = includeBuiltIn ? BUILT_IN_FRAMEWORK_OPTIONS : []
  try {
    const data = await listMaturityFrameworks(token, { signal })
    const custom = frameworkOptionsFromResponse(data).map((option) => ({
      ...option,
      builtIn: false,
    }))
    return {
      options: uniqueFrameworkOptions([...builtIn, ...custom]),
      customCount: custom.length,
      error: null,
      forbidden: false,
    }
  } catch (error) {
    if (signal?.aborted || error?.name === 'AbortError') {
      return {
        options: [...builtIn],
        customCount: 0,
        error: null,
        forbidden: false,
        aborted: true,
      }
    }
    if (isForbiddenError(error)) {
      return {
        options: [...builtIn],
        customCount: 0,
        error: null,
        forbidden: true,
      }
    }
    return {
      options: [...builtIn],
      customCount: 0,
      error: error?.message ?? 'Could not load frameworks',
      forbidden: false,
    }
  }
}

/**
 * Load catalog for UI selectors: built-ins + custom definitions when allowed.
 * Concurrent callers share one in-flight request; successful results are cached briefly.
 *
 * - 403 (non-admin): returns built-ins only, no error (expected).
 * - Other failures: returns built-ins for UX continuity but surfaces `error` (no silent fake success).
 */
export async function loadFrameworkCatalog(token, { signal, includeBuiltIn = true, force = false } = {}) {
  const cacheKey = `${Boolean(includeBuiltIn)}:${String(token ?? '')}`
  if (!force) {
    const cached = catalogCache.get(cacheKey)
    if (cached && cached.expiresAt > Date.now()) {
      return { ...cached.result, options: [...cached.result.options] }
    }
    const inflight = catalogInflight.get(cacheKey)
    if (inflight) {
      const result = await inflight
      return { ...result, options: [...(result.options ?? [])] }
    }
  }

  const request = loadFrameworkCatalogUncached(token, { signal, includeBuiltIn }).then((result) => {
    catalogInflight.delete(cacheKey)
    if (!result.aborted && !result.error) {
      catalogCache.set(cacheKey, { expiresAt: Date.now() + CATALOG_CACHE_TTL_MS, result })
    }
    return result
  })
  catalogInflight.set(cacheKey, request)
  return request
}

/** Split selected options into CreateProjectRequest fields. */
export function splitFrameworksForProjectCreate(selectedOptions) {
  const frameworks = []
  const customMaturityFrameworkIds = []
  for (const option of selectedOptions ?? []) {
    if (option?.builtIn === false && option?.id != null && String(option.id).trim() !== '') {
      const id = Number(option.id)
      if (Number.isFinite(id)) customMaturityFrameworkIds.push(id)
      continue
    }
    const code = String(option?.code ?? option?.value ?? '').trim().toUpperCase()
    if (code === 'NDI' || code === 'CMMI') frameworks.push(code)
  }
  return { frameworks, customMaturityFrameworkIds }
}

/** Slug suitable for backend code pattern: [a-z0-9][a-z0-9_]{0,79} */
export function slugFrameworkCode(raw, { maxLength = 80 } = {}) {
  const slug = String(raw ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .replace(/_+/g, '_')
  if (!slug) return ''
  const clipped = slug.slice(0, maxLength)
  if (!/^[a-z0-9]/.test(clipped)) return `f_${clipped}`.slice(0, maxLength)
  return clipped
}
