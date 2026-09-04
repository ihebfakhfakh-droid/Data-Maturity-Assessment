/** Matches backend `org.example.pfebackend.user.Role` staff roles. */
export const STAFF_ROLES = ['ADMIN', 'MANAGER', 'CONSULTANT']
const STORAGE_ROLE_KEY = 'pfe.auth.role'

export function normalizeRole(role) {
  return String(role ?? '').toUpperCase().replace(/^ROLE_/u, '')
}

export function roleFromAuth(auth) {
  const storedRole = typeof localStorage === 'undefined' ? '' : localStorage.getItem(STORAGE_ROLE_KEY)
  const claimRole = auth?.claims?.role ?? auth?.claims?.roles?.[0] ?? auth?.roles?.[0]
  return normalizeRole(auth?.role || claimRole || storedRole || '')
}

export function isStaffRole(role) {
  return STAFF_ROLES.includes(normalizeRole(role))
}

export function isClientRole(role) {
  return normalizeRole(role) === 'CLIENT'
}

export function homePathForRole(role) {
  const normalized = normalizeRole(role)
  if (normalized === 'ADMIN') return '/admin'
  if (normalized === 'MANAGER') return '/manager'
  if (normalized === 'CONSULTANT') return '/consultant'
  return '/client'
}

export function staffAssessmentEditPathForRole(role, assessmentId) {
  return `${homePathForRole(role)}/assessments/${assessmentId}/edit`
}

export function isAdminRole(role) {
  return normalizeRole(role) === 'ADMIN'
}

export function isManagerRole(role) {
  return normalizeRole(role) === 'MANAGER'
}

/** Admin or manager: can create consultants and assign clients (per backend rules). */
export function canManageStaffTeam(role) {
  return isAdminRole(role) || isManagerRole(role)
}
