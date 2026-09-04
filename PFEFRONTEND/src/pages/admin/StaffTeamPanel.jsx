import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  Copy,
  Eye,
  FolderKanban,
  FolderPlus,
  KeyRound,
  Pencil,
  RefreshCw,
  Trash2,
  TriangleAlert,
  UserCheck,
  UserCog,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import { apiFetch } from '../../api/client.js'
import { loadFrameworkCatalog, splitFrameworksForProjectCreate } from '../../api/frameworkApi.js'
import { isAdminRole, isManagerRole } from '../../auth/roles.js'
import { BtnIcon, IconBox, SectionHeading } from '../../ui/IconBox.jsx'
import { ProjectFrameworkManager } from './ProjectFrameworkManager.jsx'
import {
  DEFAULT_FRAMEWORK_OPTIONS,
  extractAssignedFrameworks,
  formatClientLabel,
  uniqueFrameworkOptions,
} from './frameworkUtils.js'

const MANAGER_HIERARCHY_LIMIT_MESSAGE =
  'Cannot assign this manager. The maximum hierarchy allowed is two levels of managers.'

function arrayFromProjectConsultantsResponse(value) {
  if (Array.isArray(value)) return value
  if (!value || typeof value !== 'object') return []
  for (const key of ['projectConsultants', 'consultants', 'availableConsultants', 'project_consultants', 'items', 'data']) {
    if (Array.isArray(value[key])) return value[key]
  }
  if (value.project && typeof value.project === 'object') {
    return arrayFromProjectConsultantsResponse(value.project)
  }
  return []
}

function consultantId(value) {
  const raw = value?.id ?? value?.consultantId ?? value?.consultant_id ?? value?.userId ?? value?.user_id
  return raw == null ? '' : String(raw)
}

function uniqueConsultants(rows) {
  const seen = new Set()
  return rows.filter((row) => {
    const id = consultantId(row)
    if (!id || seen.has(id)) return false
    seen.add(id)
    return true
  })
}

function filterAvailableConsultants(availableRows, assignedRows) {
  const assignedIds = new Set(assignedRows.map(consultantId).filter(Boolean))
  return uniqueConsultants(availableRows).filter((row) => !assignedIds.has(consultantId(row)))
}

function userLabel(user) {
  const role = user?.role ? ` · ${String(user.role).toLowerCase()}` : ''
  return `${user?.fullName ?? user?.email ?? 'User'}${role}`
}

function assigneeLabel(user) {
  const role = String(user?.role ?? '')
    .toLowerCase()
    .replace(/^\w/u, (char) => char.toUpperCase())
  const name = user?.fullName ?? user?.email ?? 'User'
  return role ? `${name} - ${role}` : name
}

function currentProjectAssigneesLabel(client) {
  const names = Array.isArray(client?.projectConsultantNames)
    ? client.projectConsultantNames
    : Array.isArray(client?.assignedStaffNames)
      ? client.assignedStaffNames
      : []
  const cleanedNames = names.map((name) => String(name ?? '').trim()).filter(Boolean)
  if (cleanedNames.length > 0) return cleanedNames.join(', ')

  const fallback =
    client?.assignedConsultantName ??
    client?.assignedStaff ??
    client?.consultantName ??
    null
  return fallback || 'none'
}

function projectRowsFromResponse(data) {
  if (Array.isArray(data)) return data
  if (!data || typeof data !== 'object') return []
  for (const field of ['project', 'currentProject']) {
    if (data[field] && typeof data[field] === 'object') return [data[field]]
  }
  for (const field of ['projects', 'items', 'content', 'records', 'data']) {
    if (Array.isArray(data[field])) return data[field]
  }
  return [data]
}

function projectLabel(project, client) {
  return (
    project?.name ??
    project?.projectName ??
    project?.title ??
    project?.label ??
    `Project ${project?.id ?? project?.projectId ?? formatClientLabel(client)}`
  )
}

function projectStatusLabel(project) {
  return project?.status ?? project?.projectStatus ?? project?.workflowStatus ?? '—'
}

function projectAssigneeLabel(project, client) {
  return (
    project?.consultantName ??
    project?.assignedConsultantName ??
    project?.consultant?.fullName ??
    project?.managerName ??
    client?.assignedConsultantName ??
    '—'
  )
}

async function tryApiFetch(candidates, options) {
  let lastErr = null
  for (const c of candidates) {
    try {
      const next = { ...(options ?? {}), method: c.method ?? options?.method }
      return await apiFetch(c.path, next)
    } catch (e) {
      lastErr = e
      const msg = String(e?.message ?? '')
      // Retry only on method/path mismatch; bubble up auth/validation errors.
      const is405 = msg.includes(' 405 ') || msg.includes('405 Method Not Allowed')
      const is404 = msg.includes(' 404 ') || msg.includes('404 Not Found')
      if (!(is405 || is404)) throw e
    }
  }
  throw lastErr ?? new Error('Request failed')
}

export function StaffTeamPanel({
  token,
  role,
  clients,
  onClientsRefresh,
  view = 'all',
  readOnly = false,
  onViewProjectDetails,
  onEditProjectAssessment,
  sharedFrameworkCatalog,
  sharedFrameworkCatalogLoading = false,
  sharedFrameworkCatalogError = '',
  onRetryFrameworkCatalog,
}) {
  const isAdmin = isAdminRole(role)
  const isManager = isManagerRole(role)
  const isConsultant = String(role ?? '').toUpperCase() === 'CONSULTANT'
  const canManageClients = isAdmin || isManager
  const canViewExistingProjects = isAdmin || isManager || isConsultant
  const showAddClient = view === 'all' || view === 'team' || view === 'team-add-client'
  const showConsultants = view === 'all' || view === 'team' || view === 'team-add-consultant'
  const showStaffList =
    view === 'all' ||
    view === 'team' ||
    view === 'team-staff-list' ||
    view === 'team-consultants-list' ||
    view === 'team-managers-list'
  const showManagersInStaffList = view !== 'team-consultants-list'
  const showConsultantsInStaffList = view !== 'team-managers-list'
  const showClientAssignment = view === 'all' || view === 'team' || view === 'team-assign-consultant'
  const showExistingProjects = view === 'all' || view === 'projects' || view === 'project-existing'
  const showCreateProject = view === 'all' || view === 'projects' || view === 'project-create'
  const showProjectsList = view === 'all' || view === 'projects' || view === 'project-list'
  const showProjectStaff = view === 'all' || view === 'projects' || view === 'project-add-consultant'

  const [teamError, setTeamError] = useState('')
  const [teamSuccess, setTeamSuccess] = useState('')
  const [managers, setManagers] = useState([])
  const [consultants, setConsultants] = useState([])
  const [staffTypeFilter, setStaffTypeFilter] = useState('all')

  const [newClientFirstName, setNewClientFirstName] = useState('')
  const [newClientLastName, setNewClientLastName] = useState('')
  const [newClientEmail, setNewClientEmail] = useState('')
  const [newClientResult, setNewClientResult] = useState(null) // { email, password, clientId }
  const [newClientModal, setNewClientModal] = useState(null) // { email, password, clientId }
  const [creatingClient, setCreatingClient] = useState(false)

  const [projectClientId, setProjectClientId] = useState('')
  const [projectFrameworkKeys, setProjectFrameworkKeys] = useState(['NDI'])
  const [localFrameworkCatalog, setLocalFrameworkCatalog] = useState(DEFAULT_FRAMEWORK_OPTIONS)
  const [localFrameworkCatalogLoading, setLocalFrameworkCatalogLoading] = useState(false)
  const [localFrameworkCatalogError, setLocalFrameworkCatalogError] = useState('')
  const [frameworkCatalogTick, setFrameworkCatalogTick] = useState(0)
  const usesSharedFrameworkCatalog = Array.isArray(sharedFrameworkCatalog)
  const frameworkCatalog = usesSharedFrameworkCatalog
    ? sharedFrameworkCatalog.length
      ? sharedFrameworkCatalog
      : DEFAULT_FRAMEWORK_OPTIONS
    : localFrameworkCatalog
  const frameworkCatalogLoading = usesSharedFrameworkCatalog
    ? Boolean(sharedFrameworkCatalogLoading)
    : localFrameworkCatalogLoading
  const frameworkCatalogError = usesSharedFrameworkCatalog
    ? sharedFrameworkCatalogError ?? ''
    : localFrameworkCatalogError

  const [projectResult, setProjectResult] = useState(null) // { projectId, clientEmail, password? }
  const [creatingProject, setCreatingProject] = useState(false)
  const [existingProjects, setExistingProjects] = useState([])
  const [existingProjectsLoading, setExistingProjectsLoading] = useState(false)
  const [existingProjectsError, setExistingProjectsError] = useState('')
  const [projectScopeClients, setProjectScopeClients] = useState([])
  const [projectScopeLoading, setProjectScopeLoading] = useState(false)
  const [projectScopeError, setProjectScopeError] = useState('')

  const [managerParentEdits, setManagerParentEdits] = useState({})
  const [updatingManagerId, setUpdatingManagerId] = useState('')

  const [consName, setConsName] = useState('')
  const [consEmail, setConsEmail] = useState('')
  const [consPassword, setConsPassword] = useState('')
  const [consManagerId, setConsManagerId] = useState('')
  const [consCanBeManager, setConsCanBeManager] = useState(false)
  const [consSuperiorManagerId, setConsSuperiorManagerId] = useState('')
  const [creatingConsultant, setCreatingConsultant] = useState(false)
  const [deletingConsultantId, setDeletingConsultantId] = useState('')
  const [confirmRemoval, setConfirmRemoval] = useState(null) // { id, name, email }
  const clientCreatedTitleId = useId()
  const confirmRemovalTitleId = useId()
  const clientCreatedCloseRef = useRef(null)
  const confirmRemovalCancelRef = useRef(null)

  const [assignClientId, setAssignClientId] = useState('')
  const [assignConsultantId, setAssignConsultantId] = useState('')
  const [assigningConsultant, setAssigningConsultant] = useState(false)
  const [assignableAssignees, setAssignableAssignees] = useState([])
  const [assignableLoading, setAssignableLoading] = useState(false)
  const [assignableError, setAssignableError] = useState('')

  const [projectConsultantClientId, setProjectConsultantClientId] = useState('')
  const [projectConsultants, setProjectConsultants] = useState([])
  const [availableProjectConsultants, setAvailableProjectConsultants] = useState([])
  const [projectConsultantId, setProjectConsultantId] = useState('')
  const [projectConsultantCanManage, setProjectConsultantCanManage] = useState(false)
  const [addingProjectConsultant, setAddingProjectConsultant] = useState(false)
  const [projectConsultantLoading, setProjectConsultantLoading] = useState(false)
  const [showProjectConsultantForm, setShowProjectConsultantForm] = useState(false)
  const [projectConsultantError, setProjectConsultantError] = useState('')

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token])
  const needsProjectScopeClients = showProjectsList || showProjectStaff
  const scopedProjectClients = needsProjectScopeClients ? projectScopeClients : clients
  const frameworkOptions = useMemo(
    () => uniqueFrameworkOptions(frameworkCatalog.length ? frameworkCatalog : DEFAULT_FRAMEWORK_OPTIONS),
    [frameworkCatalog],
  )
  const selectedProjectFrameworks = useMemo(() => {
    const selectedKeys = new Set(projectFrameworkKeys)
    return frameworkOptions.filter((option) => selectedKeys.has(option.key))
  }, [frameworkOptions, projectFrameworkKeys])
  const selectedProjectClientId = projectClientId || (clients[0]?.id != null ? String(clients[0].id) : '')
  const selectedAssignClientId = assignClientId || (clients[0]?.id != null ? String(clients[0].id) : '')
  const selectedAssignConsultantId = assignableAssignees.some((assignee) => String(assignee.id) === String(assignConsultantId))
    ? assignConsultantId
    : assignableAssignees[0]?.id != null
      ? String(assignableAssignees[0].id)
      : ''
  const selectedConsultantManagerId = consManagerId || (managers[0]?.id != null ? String(managers[0].id) : '')
  const selectedProjectConsultantClientId =
    projectConsultantClientId || (scopedProjectClients[0]?.id != null ? String(scopedProjectClients[0].id) : '')
  const selectedProjectConsultantId = availableProjectConsultants.some(
    (consultant) => String(consultant.id) === String(projectConsultantId),
  )
    ? projectConsultantId
    : availableProjectConsultants[0]?.id != null
      ? String(availableProjectConsultants[0].id)
      : ''
  const staffListTitle = view === 'team-consultants-list'
    ? 'Consultants'
    : view === 'team-managers-list'
      ? 'Managers'
      : 'Consultants & Managers'
  const staffListIcon = view === 'team-consultants-list'
    ? Users
    : view === 'team-managers-list'
      ? UserCog
      : Users
  const staffListSubtitle =
    view === 'team-consultants-list'
      ? 'Current consultants visible in your scope.'
      : view === 'team-managers-list'
        ? 'Current managers visible in your scope.'
        : isAdmin
          ? 'Review all staff users, update manager hierarchy, and remove consultant accounts.'
          : 'Staff users shown here are explicitly assigned to your management scope.'

  const canFilterStaffList = showManagersInStaffList && showConsultantsInStaffList
  const visibleStaffTypeFilter = canFilterStaffList ? staffTypeFilter : 'all'
  const displayManagersInStaffList = showManagersInStaffList && visibleStaffTypeFilter !== 'consultants'
  const displayConsultantsInStaffList = showConsultantsInStaffList && visibleStaffTypeFilter !== 'managers'
  const staffListCount =
    (displayManagersInStaffList ? managers.length : 0) + (displayConsultantsInStaffList ? consultants.length : 0)

  const reloadTeam = useCallback(async () => {
    setTeamError('')
    if (!isAdmin && !isManager) {
      setManagers([])
      setConsultants([])
      return
    }
    try {
      if (isAdmin || isManager) {
        const m = await apiFetch('/api/admin/staff/managers', { headers })
        setManagers(m ?? [])
      }
      const c = await apiFetch('/api/admin/staff/consultants', { headers })
      setConsultants(c ?? [])
    } catch (e) {
      setTeamError(e?.message ?? 'Failed to load team data')
    }
  }, [headers, isAdmin, isManager])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!cancelled) await reloadTeam()
    }
    run()
    return () => {
      cancelled = true
    }
  }, [reloadTeam])

  useEffect(() => {
    if (usesSharedFrameworkCatalog) return undefined
    let cancelled = false
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
    async function run() {
      setLocalFrameworkCatalogLoading(true)
      const catalog = await loadFrameworkCatalog(token, {
        signal: controller?.signal,
        force: frameworkCatalogTick > 0,
      })
      if (cancelled || catalog.aborted) return
      setLocalFrameworkCatalog(catalog.options.length ? catalog.options : DEFAULT_FRAMEWORK_OPTIONS)
      setLocalFrameworkCatalogError(catalog.error ?? '')
      setLocalFrameworkCatalogLoading(false)
    }
    run()
    return () => {
      cancelled = true
      controller?.abort()
    }
  }, [token, frameworkCatalogTick, usesSharedFrameworkCatalog])

  useEffect(() => {
    if (!showExistingProjects || !canViewExistingProjects) return undefined

    let cancelled = false
    async function run() {
      setExistingProjectsLoading(true)
      setExistingProjectsError('')
      try {
        const rows = await Promise.all(
          clients.map(async (client) => {
            try {
              const data = await apiFetch(`/api/admin/clients/${client.id}/project`, { headers })
              return projectRowsFromResponse(data).map((project) => ({ client, project }))
            } catch {
              return []
            }
          }),
        )
        if (!cancelled) setExistingProjects(rows.flat())
      } catch (err) {
        if (!cancelled) setExistingProjectsError(err?.message ?? 'Could not load existing projects')
      } finally {
        if (!cancelled) setExistingProjectsLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [canViewExistingProjects, clients, headers, showExistingProjects])

  useEffect(() => {
    if (!needsProjectScopeClients || !(isAdmin || isManager)) return undefined

    let cancelled = false
    async function run() {
      setProjectScopeLoading(true)
      setProjectScopeError('')
      try {
        const rows = await apiFetch('/api/admin/clients/project-scope', { headers })
        if (!cancelled) {
          const nextRows = Array.isArray(rows) ? rows : []
          setProjectScopeClients(nextRows)
          const ids = new Set(nextRows.map((client) => String(client.id)))
          if (projectConsultantClientId && !ids.has(String(projectConsultantClientId))) {
            setProjectConsultantClientId('')
          }
        }
      } catch (err) {
        if (!cancelled) {
          setProjectScopeClients([])
          setProjectScopeError(err?.message ?? 'Could not load project clients')
        }
      } finally {
        if (!cancelled) setProjectScopeLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [headers, isAdmin, isManager, needsProjectScopeClients, projectConsultantClientId])

  const reloadProjectConsultants = useCallback(
    async (clientId = selectedProjectConsultantClientId) => {
      if (!clientId || !(isAdmin || isManager)) return
      setProjectConsultantLoading(true)
      setProjectConsultantError('')
      try {
        const [projectDetail, assigned, available] = await Promise.all([
          apiFetch(`/api/admin/clients/${clientId}/project`, { headers }).catch(() => null),
          apiFetch(`/api/admin/clients/${clientId}/project/consultants`, { headers }),
          apiFetch(`/api/admin/clients/${clientId}/project/consultants/available`, { headers }),
        ])
        const assignedRows = uniqueConsultants([
          ...arrayFromProjectConsultantsResponse(projectDetail),
          ...arrayFromProjectConsultantsResponse(assigned),
        ])
        setProjectConsultants(assignedRows)
        setAvailableProjectConsultants(filterAvailableConsultants(arrayFromProjectConsultantsResponse(available), assignedRows))
      } catch (err) {
        setProjectConsultants([])
        setAvailableProjectConsultants([])
        setProjectConsultantId('')
        setProjectConsultantError(err?.message ?? 'Could not load project assignees')
      } finally {
        setProjectConsultantLoading(false)
      }
    },
    [headers, isAdmin, isManager, selectedProjectConsultantClientId],
  )

  useEffect(() => {
    if (!selectedProjectConsultantClientId || !(isAdmin || isManager)) return undefined
    let cancelled = false
    async function run() {
      setProjectConsultantLoading(true)
      setProjectConsultantError('')
      try {
        const [projectDetail, assigned, available] = await Promise.all([
          apiFetch(`/api/admin/clients/${selectedProjectConsultantClientId}/project`, { headers }).catch(() => null),
          apiFetch(`/api/admin/clients/${selectedProjectConsultantClientId}/project/consultants`, { headers }),
          apiFetch(`/api/admin/clients/${selectedProjectConsultantClientId}/project/consultants/available`, { headers }),
        ])
        if (!cancelled) {
          const assignedRows = uniqueConsultants([
            ...arrayFromProjectConsultantsResponse(projectDetail),
            ...arrayFromProjectConsultantsResponse(assigned),
          ])
          setProjectConsultants(assignedRows)
          setAvailableProjectConsultants(filterAvailableConsultants(arrayFromProjectConsultantsResponse(available), assignedRows))
        }
      } catch (err) {
        if (!cancelled) {
          setProjectConsultants([])
          setAvailableProjectConsultants([])
          setProjectConsultantId('')
          setProjectConsultantError(err?.message ?? 'Could not load project assignees')
        }
      } finally {
        if (!cancelled) setProjectConsultantLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [headers, isAdmin, isManager, selectedProjectConsultantClientId])

  useEffect(() => {
    if (!showClientAssignment || !selectedAssignClientId || !(isAdmin || isManager)) return undefined
    let cancelled = false
    async function run() {
      setAssignableLoading(true)
      setAssignableError('')
      try {
        const [assigned, available] = await Promise.all([
          apiFetch(`/api/admin/clients/${selectedAssignClientId}/project/consultants`, { headers }),
          apiFetch(`/api/admin/clients/${selectedAssignClientId}/project/consultants/available`, { headers }),
        ])
        if (!cancelled) {
          const assignedRows = arrayFromProjectConsultantsResponse(assigned)
          const availableRows = filterAvailableConsultants(arrayFromProjectConsultantsResponse(available), assignedRows)
          setAssignableAssignees(availableRows)
          if (!availableRows.some((assignee) => String(assignee.id) === String(assignConsultantId))) {
            setAssignConsultantId('')
          }
        }
      } catch (err) {
        if (!cancelled) {
          setAssignableAssignees([])
          setAssignConsultantId('')
          setAssignableError(err?.message ?? 'Could not load assignable people')
        }
      } finally {
        if (!cancelled) setAssignableLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [assignConsultantId, headers, isAdmin, isManager, selectedAssignClientId, showClientAssignment])

  async function copyToClipboard(text) {
    const t = String(text ?? '')
    if (!t) return
    try {
      await navigator.clipboard.writeText(t)
      setTeamSuccess('Copied to clipboard.')
      setTimeout(() => setTeamSuccess(''), 1200)
    } catch {
      // ignore (browser permissions)
    }
  }

  function downloadTextFile(filename, content) {
    const safeName = String(filename ?? 'credentials.txt')
    const blob = new Blob([String(content ?? '')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = safeName
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  function downloadClientCredentialsTxt({ email, password, clientId }) {
    const lines = [
      'Client account created',
      clientId ? `Client ID: ${clientId}` : null,
      email ? `Email: ${email}` : null,
      password ? `Password: ${password}` : null,
      '',
      `Generated at: ${new Date().toISOString()}`,
    ].filter(Boolean)
    const safeEmail = String(email ?? 'client').replaceAll(/[^a-zA-Z0-9._-]/g, '_')
    downloadTextFile(`client-credentials-${safeEmail}.txt`, lines.join('\n'))
  }

  function normalizeFrameworks() {
    return splitFrameworksForProjectCreate(selectedProjectFrameworks)
  }

  function toggleProjectFramework(frameworkKey, checked) {
    setProjectFrameworkKeys((prev) => {
      if (checked) return prev.includes(frameworkKey) ? prev : [...prev, frameworkKey]
      return prev.filter((key) => key !== frameworkKey)
    })
  }

  function managerParentValue(manager) {
    const raw = manager?.managerId ?? manager?.managedById ?? manager?.parentManagerId ?? manager?.superiorManagerId
    return raw == null ? '' : String(raw)
  }

  function managerById(managerId) {
    const id = String(managerId ?? '')
    return managers.find((manager) => String(manager.id) === id) ?? null
  }

  function managerParentLabel(manager) {
    const directName =
      manager?.managerName ??
      manager?.managedByName ??
      manager?.parentManagerName ??
      manager?.superiorManagerName ??
      manager?.manager?.fullName ??
      manager?.managedBy?.fullName ??
      manager?.superiorManager?.fullName
    if (directName) return directName
    const parent = managerById(managerParentValue(manager))
    return parent?.fullName ?? parent?.email ?? '—'
  }

  function isTopLevelManager(managerId) {
    const manager = managerById(managerId)
    return Boolean(manager) && !managerParentValue(manager)
  }

  function managerEditValue(manager) {
    const id = String(manager?.id ?? '')
    return managerParentEdits[id] ?? managerParentValue(manager)
  }

  function managedManagersFor(managerId) {
    const id = String(managerId ?? '')
    return managers.filter((manager) => managerParentValue(manager) === id)
  }

  function managerDescendantIds(managerId, visited = new Set()) {
    const id = String(managerId ?? '')
    if (!id || visited.has(id)) return visited
    for (const child of managedManagersFor(id)) {
      const childId = String(child.id ?? '')
      if (!childId || visited.has(childId)) continue
      visited.add(childId)
      managerDescendantIds(childId, visited)
    }
    return visited
  }

  function canAssignManagerParent(managerId, nextParentId) {
    if (!nextParentId) return true
    if (!isTopLevelManager(nextParentId)) return false
    return managedManagersFor(managerId).length === 0
  }

  async function onUpdateManagerParent(manager) {
    const id = manager?.id
    if (!id || updatingManagerId) return

    const nextParentId = managerEditValue(manager)
    if (nextParentId && String(nextParentId) === String(id)) {
      setTeamError('A manager cannot be their own superior manager.')
      return
    }
    if (nextParentId && managerDescendantIds(id).has(String(nextParentId))) {
      setTeamError('A manager cannot be assigned under one of their subordinate managers.')
      return
    }
    if (!canAssignManagerParent(id, nextParentId)) {
      setTeamError(MANAGER_HIERARCHY_LIMIT_MESSAGE)
      return
    }

    setTeamError('')
    setTeamSuccess('')
    setUpdatingManagerId(String(id))
    try {
      const body = JSON.stringify({ managerId: nextParentId ? Number(nextParentId) : null })
      await apiFetch(`/api/admin/staff/managers/${id}/manager`, { method: 'PATCH', headers, body })
      setTeamSuccess('Manager hierarchy updated.')
      setManagerParentEdits((prev) => {
        const next = { ...prev }
        delete next[String(id)]
        return next
      })
      await reloadTeam()
    } catch (err) {
      setTeamError(err?.message ?? 'Could not update manager hierarchy')
    } finally {
      setUpdatingManagerId('')
    }
  }

  async function onAddNewClient(e) {
    e.preventDefault()
    if (creatingClient) return
    setTeamError('')
    setTeamSuccess('')
    setNewClientResult(null)
    setNewClientModal(null)
    setCreatingClient(true)
    try {
      const firstName = newClientFirstName.trim()
      const lastName = newClientLastName.trim()
      const email = newClientEmail.trim()
      const fullName = `${firstName} ${lastName}`.trim()

      const body = JSON.stringify({ firstName, lastName, fullName, email })
      const res = await tryApiFetch(
        [
          // Expected backend endpoint (returns generatedPassword)
          { method: 'POST', path: '/api/admin/staff/clients' },
          { method: 'POST', path: '/api/admin/clients' },
          { method: 'POST', path: '/api/admin/clients/create' },
          { method: 'POST', path: '/api/admin/clients/new' },
          { method: 'POST', path: '/api/admin/client' },
          { method: 'POST', path: '/api/admin/client/create' },
          { method: 'POST', path: '/api/admin/clients/add' },
          { method: 'PUT', path: '/api/admin/clients' },
          { method: 'PUT', path: '/api/admin/client' },
        ],
        { headers, body },
      )

      const password =
        res?.password ??
        res?.generatedPassword ??
        res?.tempPassword ??
        res?.initialPassword ??
        ''
      const clientId = res?.id ?? res?.clientId ?? null
      const result = { email, password, clientId }
      setNewClientResult(result)
      setNewClientModal(result)
      if (password) downloadClientCredentialsTxt(result)
      setNewClientFirstName('')
      setNewClientLastName('')
      setNewClientEmail('')
      await onClientsRefresh()
    } catch (err) {
      setTeamError(err?.message ?? 'Could not create client')
    } finally {
      setCreatingClient(false)
    }
  }

  async function onCreateProject(e) {
    e.preventDefault()
    if (creatingProject) return
    if (!selectedProjectClientId) return
    const { frameworks, customMaturityFrameworkIds } = normalizeFrameworks()
    if (frameworks.length === 0 && customMaturityFrameworkIds.length === 0) {
      setTeamError('Pick at least one framework.')
      return
    }
    setTeamError('')
    setTeamSuccess('')
    setProjectResult(null)
    setCreatingProject(true)
    try {
      const body = JSON.stringify({
        clientId: Number(selectedProjectClientId),
        frameworks,
        customMaturityFrameworkIds,
        consultantId: null,
        assignedStaff: null,
        canManageProject: false,
      })
      const res = await tryApiFetch(
        [
          { method: 'POST', path: '/api/admin/projects' },
          { method: 'POST', path: '/api/admin/projects/create' },
          { method: 'POST', path: '/api/admin/project' },
          { method: 'POST', path: '/api/admin/project/create' },
          { method: 'POST', path: '/api/admin/clients/project' },
          { method: 'POST', path: '/api/admin/clients/projects' },
          { method: 'PUT', path: '/api/admin/projects' },
          { method: 'PUT', path: '/api/admin/project' },
        ],
        { headers, body },
      )
      setProjectResult({
        projectId: res?.id ?? res?.projectId ?? null,
        clientEmail: res?.clientEmail ?? res?.email ?? null,
        password:
          res?.password ??
          res?.generatedPassword ??
          res?.tempPassword ??
          res?.initialPassword ??
          '',
      })
      await onClientsRefresh()
    } catch (err) {
      setTeamError(err?.message ?? 'Could not create project')
    } finally {
      setCreatingProject(false)
    }
  }

  async function onCreateConsultant(e) {
    e.preventDefault()
    if (creatingConsultant) return
    setTeamError('')
    setTeamSuccess('')
    setCreatingConsultant(true)
    try {
      if (consCanBeManager) {
        if (consSuperiorManagerId && !isTopLevelManager(consSuperiorManagerId)) {
          setTeamError(MANAGER_HIERARCHY_LIMIT_MESSAGE)
          setCreatingConsultant(false)
          return
        }
        await apiFetch('/api/admin/staff/managers', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            fullName: consName.trim(),
            email: consEmail.trim(),
            password: consPassword,
            managerId: consSuperiorManagerId ? Number(consSuperiorManagerId) : null,
          }),
        })
      } else {
        const body =
          isAdmin && selectedConsultantManagerId
            ? {
                fullName: consName.trim(),
                email: consEmail.trim(),
                password: consPassword,
                managerId: Number(selectedConsultantManagerId),
              }
            : {
                fullName: consName.trim(),
                email: consEmail.trim(),
                password: consPassword,
              }
        await apiFetch('/api/admin/staff/consultants', {
          method: 'POST',
          headers,
          body: JSON.stringify(body),
        })
      }
      setConsName('')
      setConsEmail('')
      setConsPassword('')
      setConsManagerId('')
      setConsSuperiorManagerId('')
      setConsCanBeManager(false)
      await reloadTeam()
    } catch (err) {
      setTeamError(err?.message ?? 'Could not create staff user')
    } finally {
      setCreatingConsultant(false)
    }
  }

  async function onDeleteConsultant(consultantId) {
    if (deletingConsultantId) return
    setTeamError('')
    setTeamSuccess('')
    setDeletingConsultantId(String(consultantId))
    try {
      await apiFetch(`/api/admin/staff/consultants/${consultantId}`, {
        method: 'DELETE',
        headers,
      })
      setConfirmRemoval(null)
      await reloadTeam()
      await onClientsRefresh()
    } catch (err) {
      setTeamError(err?.message ?? 'Could not delete consultant')
    } finally {
      setDeletingConsultantId('')
    }
  }

  function requestRemoveConsultant(consultant) {
    setConfirmRemoval({
      id: consultant.id,
      name: consultant.fullName ?? consultant.email ?? 'this consultant',
      email: consultant.email ?? '',
    })
  }

  async function onAssign(e) {
    e.preventDefault()
    if (assigningConsultant) return
    if (!selectedAssignClientId || !selectedAssignConsultantId) return
    setTeamError('')
    setTeamSuccess('')
    setAssigningConsultant(true)
    try {
      await apiFetch(`/api/admin/clients/${selectedAssignClientId}/project/consultants`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          consultantId: Number(selectedAssignConsultantId),
          canManageProject: false,
        }),
      })
      setTeamSuccess('Assignee added to project.')
      setAssignConsultantId('')
      await onClientsRefresh()
    } catch (err) {
      setTeamError(err?.message ?? 'Could not assign this person')
    } finally {
      setAssigningConsultant(false)
    }
  }

  async function onAddProjectConsultant(e) {
    e.preventDefault()
    if (addingProjectConsultant) return
    if (!selectedProjectConsultantClientId || !selectedProjectConsultantId) return
    setTeamError('')
    setTeamSuccess('')
    setProjectConsultantError('')
    setAddingProjectConsultant(true)
    try {
      await apiFetch(`/api/admin/clients/${selectedProjectConsultantClientId}/project/consultants`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          consultantId: Number(selectedProjectConsultantId),
          canManageProject: Boolean(projectConsultantCanManage),
        }),
      })
      setTeamSuccess('Consultant added to project.')
      setShowProjectConsultantForm(false)
      setProjectConsultantCanManage(false)
      await reloadProjectConsultants(selectedProjectConsultantClientId)
      await onClientsRefresh()
    } catch (err) {
      setProjectConsultantError(err?.message ?? 'Could not add consultant to project')
    } finally {
      setAddingProjectConsultant(false)
    }
  }

  useEffect(() => {
    if (!newClientModal && !confirmRemoval) return undefined
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const timer = window.setTimeout(() => {
      if (confirmRemoval) confirmRemovalCancelRef.current?.focus()
      else clientCreatedCloseRef.current?.focus()
    }, 0)
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        if (confirmRemoval) setConfirmRemoval(null)
        else setNewClientModal(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [newClientModal, confirmRemoval])

  return (
    <div className="teamLayout">
      {teamError ? <div className="alert alertError">{teamError}</div> : null}
      {teamSuccess ? <div className="alert alertSuccess">{teamSuccess}</div> : null}

      {newClientModal ? (
        <div
          className="staffDialogBackdrop"
          role="presentation"
          onClick={() => setNewClientModal(null)}
        >
          <div
            className="staffDialogPanel"
            role="dialog"
            aria-modal="true"
            aria-labelledby={clientCreatedTitleId}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="staffDialogHeader">
              <div className="staffDialogHeading">
                <IconBox>
                  <UserCheck size={22} strokeWidth={2.25} />
                </IconBox>
                <div>
                  <h2 id={clientCreatedTitleId} className="staffDialogTitle">
                    Client Created
                  </h2>
                  <p className="staffDialogSubtitle">Save these credentials now. The password is shown only once.</p>
                </div>
              </div>
              <button
                ref={clientCreatedCloseRef}
                type="button"
                className="staffDialogClose"
                aria-label="Close"
                onClick={() => setNewClientModal(null)}
              >
                <X size={18} strokeWidth={2.25} aria-hidden="true" />
              </button>
            </div>
            <div className="staffDialogBody">
              <div className="staffDialogInfoCard">
                <div className="staffDialogInfoLabel">Email</div>
                <div className="staffDialogInfoValue">
                  <span className="monoCell">{newClientModal.email}</span>
                  <button
                    type="button"
                    className="btn btnGhost btnSm btnWithIcon"
                    onClick={() => copyToClipboard(newClientModal.email)}
                    aria-label="Copy email"
                  >
                    <BtnIcon icon={Copy} />
                    Copy
                  </button>
                </div>
              </div>
              <div className="staffDialogInfoCard">
                <div className="staffDialogInfoLabel">Generated password</div>
                <div className="staffDialogInfoValue">
                  <span className="monoCell">
                    {newClientModal.password ? newClientModal.password : '— (not returned by API)'}
                  </span>
                  {newClientModal.password ? (
                    <button
                      type="button"
                      className="btn btnGhost btnSm btnWithIcon"
                      onClick={() => copyToClipboard(newClientModal.password)}
                      aria-label="Copy password"
                    >
                      <BtnIcon icon={Copy} />
                      Copy
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="staffDialogActions">
                <button type="button" className="btn btnGhost" onClick={() => setNewClientModal(null)}>
                  Close
                </button>
                <button
                  type="button"
                  className="btn btnPrimary btnWithIcon"
                  disabled={!newClientModal.password}
                  onClick={() => downloadClientCredentialsTxt(newClientModal)}
                >
                  <BtnIcon icon={KeyRound} />
                  Download .txt
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {confirmRemoval ? (
        <div
          className="staffDialogBackdrop"
          role="presentation"
          onClick={() => setConfirmRemoval(null)}
        >
          <div
            className="staffDialogPanel"
            role="dialog"
            aria-modal="true"
            aria-labelledby={confirmRemovalTitleId}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="staffDialogHeader">
              <div className="staffDialogHeading">
                <IconBox>
                  <TriangleAlert size={22} strokeWidth={2.25} />
                </IconBox>
                <div>
                  <h2 id={confirmRemovalTitleId} className="staffDialogTitle">
                    Remove Consultant
                  </h2>
                  <p className="staffDialogSubtitle">
                    This action cannot be undone from this screen.
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="staffDialogClose"
                aria-label="Close"
                onClick={() => setConfirmRemoval(null)}
              >
                <X size={18} strokeWidth={2.25} aria-hidden="true" />
              </button>
            </div>
            <div className="staffDialogBody">
              <p className="staffDialogSubtitle" style={{ margin: 0 }}>
                Remove <strong>{confirmRemoval.name}</strong>
                {confirmRemoval.email ? (
                  <>
                    {' '}
                    (<span className="monoCell">{confirmRemoval.email}</span>)
                  </>
                ) : null}
                ? Assigned clients will be unassigned.
              </p>
              <div className="staffDialogActions">
                <button
                  ref={confirmRemovalCancelRef}
                  type="button"
                  className="btn btnGhost"
                  onClick={() => setConfirmRemoval(null)}
                  disabled={Boolean(deletingConsultantId)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btnDanger btnWithIcon"
                  disabled={Boolean(deletingConsultantId)}
                  onClick={() => onDeleteConsultant(confirmRemoval.id)}
                >
                  <BtnIcon icon={Trash2} />
                  {deletingConsultantId ? 'Removing…' : 'Confirm Removal'}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {showExistingProjects && canViewExistingProjects ? (
        <section className="sectionCard">
          <div className="sectionHeader">
            <SectionHeading
              icon={FolderKanban}
              title="Existing Projects"
              subtitle={isConsultant ? 'Projects assigned to you.' : 'Projects currently linked to visible clients.'}
              badge={existingProjects.length}
            />
          </div>
          {existingProjectsError ? <div className="alert alertError">{existingProjectsError}</div> : null}
          {existingProjectsLoading ? <p className="muted">Loading projects...</p> : null}
          <div className="tableWrap proTableWrap proTableDesktopOnly">
            <table className="dataTable proTable">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Client</th>
                  <th>Framework</th>
                  <th>Assigned staff</th>
                  <th>Status</th>
                  {onViewProjectDetails || onEditProjectAssessment ? <th aria-label="Actions" /> : null}
                </tr>
              </thead>
              <tbody>
                {existingProjects.map(({ client, project }) => {
                  const frameworks = extractAssignedFrameworks(project)
                  const projectId = project?.id ?? project?.projectId ?? project?.project_id ?? client.id
                  return (
                    <tr key={`${client.id}-${projectId}`}>
                      <td>
                        <strong>{projectLabel(project, client)}</strong>
                        <div className="tinyNote">ID: {projectId ?? '—'}</div>
                      </td>
                      <td>{formatClientLabel(client)}</td>
                      <td>
                        {frameworks.length > 0
                          ? frameworks.map((framework) => framework.label ?? framework.value ?? framework.key).join(', ')
                          : '—'}
                      </td>
                      <td>{projectAssigneeLabel(project, client)}</td>
                      <td><span className="proBadge proBadgeNeutral">{projectStatusLabel(project)}</span></td>
                      {onViewProjectDetails || onEditProjectAssessment ? (
                        <td className="cellActions">
                          {onViewProjectDetails ? (
                            <button
                              type="button"
                              className="btn btnGhost btnSm btnWithIcon"
                              onClick={() => onViewProjectDetails(client, project)}
                            >
                              <BtnIcon icon={Eye} />
                              View Details
                            </button>
                          ) : null}
                          {onEditProjectAssessment ? (
                            <button
                              type="button"
                              className="btn btnPrimary btnSm btnWithIcon"
                              onClick={() => onEditProjectAssessment(client, project)}
                            >
                              <BtnIcon icon={Pencil} />
                              Edit
                            </button>
                          ) : null}
                        </td>
                      ) : null}
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {!existingProjectsLoading && existingProjects.length === 0 ? (
              <div className="proEmptyState">No existing projects found.</div>
            ) : null}
          </div>

          <div className="proMobileList">
            {!existingProjectsLoading && existingProjects.length === 0 ? (
              <div className="proEmptyState">No existing projects found.</div>
            ) : (
              existingProjects.map(({ client, project }) => {
                const frameworks = extractAssignedFrameworks(project)
                const projectId = project?.id ?? project?.projectId ?? project?.project_id ?? client.id
                return (
                  <article key={`m-${client.id}-${projectId}`} className="proMobileCard">
                    <div>
                      <strong>{projectLabel(project, client)}</strong>
                      <div className="tinyNote">ID: {projectId ?? '—'}</div>
                    </div>
                    <div>
                      <span className="proMobileLabel">Client</span>
                      {formatClientLabel(client)}
                    </div>
                    <div>
                      <span className="proMobileLabel">Framework</span>
                      {frameworks.length > 0
                        ? frameworks.map((framework) => framework.label ?? framework.value ?? framework.key).join(', ')
                        : '—'}
                    </div>
                    <div>
                      <span className="proMobileLabel">Status</span>
                      <span className="proBadge proBadgeNeutral">{projectStatusLabel(project)}</span>
                    </div>
                    {onViewProjectDetails || onEditProjectAssessment ? (
                      <div className="cellActions">
                        {onViewProjectDetails ? (
                          <button
                            type="button"
                            className="btn btnGhost btnSm btnWithIcon"
                            onClick={() => onViewProjectDetails(client, project)}
                          >
                            <BtnIcon icon={Eye} />
                            View Details
                          </button>
                        ) : null}
                        {onEditProjectAssessment ? (
                          <button
                            type="button"
                            className="btn btnPrimary btnSm btnWithIcon"
                            onClick={() => onEditProjectAssessment(client, project)}
                          >
                            <BtnIcon icon={Pencil} />
                            Edit
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                )
              })
            )}
          </div>
        </section>
      ) : null}

      {showAddClient && canManageClients ? (
        <section className="sectionCard">
          <div className="sectionHeader">
            <h2 className="sectionTitle">Add new client</h2>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            {isManager
              ? 'Create a client account in your manager scope. The backend should attach this client to your manager account automatically.'
              : 'Create a client account. Password is generated automatically by the backend.'}
          </p>
          <form className="form" onSubmit={onAddNewClient}>
            <div className="formSection">
              <div className="formSectionHeader">
                <span className="formSectionEyebrow">Client account</span>
                <h3 className="formSectionTitle">Personal information</h3>
              </div>
              <div className="fieldRow">
                <label className="field">
                  <span className="label">First name</span>
                  <input
                    className="input"
                    value={newClientFirstName}
                    onChange={(e) => setNewClientFirstName(e.target.value)}
                    placeholder="Client first name"
                    required
                  />
                </label>
                <label className="field">
                  <span className="label">Last name</span>
                  <input
                    className="input"
                    value={newClientLastName}
                    onChange={(e) => setNewClientLastName(e.target.value)}
                    placeholder="Client last name"
                    required
                  />
                </label>
                <label className="field">
                  <span className="label">Email</span>
                  <input
                    className="input"
                    type="email"
                    value={newClientEmail}
                    onChange={(e) => setNewClientEmail(e.target.value)}
                    placeholder="client@company.com"
                    required
                  />
                </label>
              </div>
            </div>
            <div className="formActions">
              <button type="submit" className="btn btnPrimary" disabled={creatingClient}>
                {creatingClient ? 'Creating...' : 'Create client'}
              </button>
            </div>
          </form>

          {newClientResult ? (
            <div className="alert alertSuccess" style={{ marginTop: 12 }}>
              <div style={{ display: 'grid', gap: 8 }}>
                <div>
                  Email: <strong className="monoCell">{newClientResult.email}</strong>{' '}
                  <button type="button" className="btn btnGhost btnSm" onClick={() => copyToClipboard(newClientResult.email)}>
                    Copy
                  </button>
                </div>
                <div>
                  Password:{' '}
                  <strong className="monoCell">{newClientResult.password ? newClientResult.password : '— (not returned by API)'}</strong>{' '}
                  {newClientResult.password ? (
                    <button type="button" className="btn btnGhost btnSm" onClick={() => copyToClipboard(newClientResult.password)}>
                      Copy
                    </button>
                  ) : null}
                </div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btnGhost btnSm"
                    onClick={() => setNewClientModal(newClientResult)}
                  >
                    Show modal
                  </button>
                  <button
                    type="button"
                    className="btn btnGhost btnSm"
                    disabled={!newClientResult.password}
                    onClick={() => downloadClientCredentialsTxt(newClientResult)}
                  >
                    Download .txt
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {showCreateProject && (isAdmin || isManager) ? (
        <section className="sectionCard">
          <div className="sectionHeader">
            <SectionHeading
              icon={FolderPlus}
              title="Create Project"
              subtitle="Link an existing client and assign one or more available frameworks."
            />
          </div>
          <form className="form" onSubmit={onCreateProject}>
            <div className="formSection">
              <div className="formSectionHeader">
                <span className="formSectionEyebrow">Project setup</span>
                <h3 className="formSectionTitle">Client and framework</h3>
              </div>
              <div className="fieldRow">
                <label className="field">
                  <span className="label">Client</span>
                  <select className="select selectScrollable" value={selectedProjectClientId} onChange={(e) => setProjectClientId(e.target.value)} required>
                    {clients.map((cl) => (
                      <option key={cl.id} value={cl.id}>
                        {cl.fullName ?? cl.email} ({cl.email})
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span className="label">Frameworks</span>
                  <div className="optionGrid">
                    {frameworkOptions.map((option) => (
                      <label key={option.key} className="checkOption">
                        <input
                          type="checkbox"
                          checked={projectFrameworkKeys.includes(option.key)}
                          onChange={(e) => toggleProjectFramework(option.key, e.target.checked)}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                  </div>
                  {frameworkCatalogLoading ? <span className="muted">Loading frameworks...</span> : null}
                  {frameworkCatalogError ? (
                    <div className="alert alertError" style={{ marginTop: 8 }}>
                      {frameworkCatalogError}
                      <div style={{ marginTop: 8 }}>
                        <button
                          type="button"
                          className="btn btnGhost btnSm btnWithIcon"
                          onClick={() =>
                            usesSharedFrameworkCatalog
                              ? onRetryFrameworkCatalog?.()
                              : setFrameworkCatalogTick((n) => n + 1)
                          }
                        >
                          <BtnIcon icon={RefreshCw} />
                          Retry
                        </button>
                      </div>
                    </div>
                  ) : null}
                </label>
              </div>
            </div>
            <div className="formActions">
              <button
                type="submit"
                className="btn btnPrimary btnWithIcon"
                disabled={creatingProject || clients.length === 0 || selectedProjectFrameworks.length === 0 || frameworkCatalogLoading}
              >
                <BtnIcon icon={FolderPlus} />
                {creatingProject ? 'Creating...' : 'Create Project'}
              </button>
            </div>
            {clients.length === 0 ? <p className="muted">No clients found. Create a client first.</p> : null}
          </form>

          {projectResult ? (
            <div className="alert alertSuccess" style={{ marginTop: 12 }}>
              <div style={{ display: 'grid', gap: 8 }}>
                <div>
                  Project ID: <strong className="monoCell">{projectResult.projectId ?? '—'}</strong>
                </div>
                <div>
                  Client email:{' '}
                  <strong className="monoCell">{projectResult.clientEmail ?? '— (not returned by API)'}</strong>
                </div>
                <div>
                  Password:{' '}
                  <strong className="monoCell">{projectResult.password ? projectResult.password : '— (not returned by API)'}</strong>
                  {projectResult.password ? (
                    <>
                      {' '}
                      <button type="button" className="btn btnGhost btnSm" onClick={() => copyToClipboard(projectResult.password)}>
                        Copy
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {showProjectsList && (isAdmin || isManager) ? (
        <>
          {projectScopeError ? <div className="alert alertError">{projectScopeError}</div> : null}
          {projectScopeLoading ? <p className="muted">Loading project clients...</p> : null}
          <ProjectFrameworkManager
            token={token}
            clients={scopedProjectClients}
            onClientsRefresh={onClientsRefresh}
            title="Add Framework To Project"
            description="Select a client project, review its assigned frameworks, and add another framework without changing previous answers, evidence, and history."
            sharedFrameworkCatalog={frameworkCatalog}
            sharedFrameworkCatalogLoading={frameworkCatalogLoading}
            sharedFrameworkCatalogError={frameworkCatalogError}
            onRetryFrameworkCatalog={() =>
              usesSharedFrameworkCatalog
                ? onRetryFrameworkCatalog?.()
                : setFrameworkCatalogTick((n) => n + 1)
            }
          />
        </>
      ) : null}

      {showProjectStaff && (isAdmin || isManager) ? (
        <section className="sectionCard">
          <div className="sectionHeader">
            <h2 className="sectionTitle">Add Consultant To Project</h2>
            <div className="badge">{projectConsultants.length}</div>
          </div>
          <p className="muted" style={{ marginTop: 0 }}>
            Select a client project, review assignees already associated with it, and add a consultant or manager.
          </p>

          <div className="form">
            <label className="field">
              <span className="label">Client project</span>
              <select
                className="select selectScrollable"
                value={selectedProjectConsultantClientId}
                onChange={(e) => {
                  setProjectConsultantClientId(e.target.value)
                  setShowProjectConsultantForm(false)
                  setProjectConsultantId('')
                }}
                disabled={projectScopeLoading || scopedProjectClients.length === 0}
              >
                {scopedProjectClients.map((cl) => (
                  <option key={cl.id} value={cl.id}>
                    {cl.fullName ?? cl.email} ({cl.email})
                  </option>
                ))}
              </select>
            </label>

            {projectScopeError ? <div className="alert alertError">{projectScopeError}</div> : null}
            {projectScopeLoading ? <p className="muted">Loading project clients...</p> : null}
            {projectConsultantError ? <div className="alert alertError">{projectConsultantError}</div> : null}

            <div style={{ display: 'grid', gap: 8 }}>
              <span className="label">Assignees associated with this project</span>
              {projectConsultantLoading ? <span className="muted">Loading project assignees...</span> : null}
              {!projectConsultantLoading && projectConsultants.length === 0 ? (
                <span className="muted">No assignee associated with this project yet.</span>
              ) : null}
              {projectConsultants.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {projectConsultants.map((consultant) => (
                    <span key={consultant.id} className="badge">
                      {userLabel(consultant)}
                      {consultant.canManageProject ? ' · can manage' : ''}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>

            {!showProjectConsultantForm ? (
              <button
                type="button"
                className="btn btnPrimary"
                style={{ width: 'fit-content' }}
                disabled={scopedProjectClients.length === 0 || projectScopeLoading || projectConsultantLoading || availableProjectConsultants.length === 0}
                onClick={() => setShowProjectConsultantForm(true)}
              >
                Add consultant or manager to project
              </button>
            ) : (
              <form className="form" onSubmit={onAddProjectConsultant}>
                <label className="field">
                  <span className="label">Available consultants / managers</span>
                  <select
                    className="select selectScrollable"
                    value={selectedProjectConsultantId}
                    onChange={(e) => setProjectConsultantId(e.target.value)}
                    required
                  >
                    {availableProjectConsultants.map((consultant) => (
                      <option key={consultant.id} value={consultant.id}>
                        {userLabel(consultant)} ({consultant.email})
                      </option>
                    ))}
                  </select>
                  {availableProjectConsultants.length === 0 ? (
                    <span className="muted">No available consultant or manager for this project.</span>
                  ) : null}
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={projectConsultantCanManage}
                    onChange={(e) => setProjectConsultantCanManage(e.target.checked)}
                  />
                  Allow this user to manage the project
                </label>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button
                    type="submit"
                    className="btn btnPrimary"
                    style={{ width: 'fit-content' }}
                    disabled={addingProjectConsultant || availableProjectConsultants.length === 0}
                  >
                    {addingProjectConsultant ? 'Adding...' : 'Confirm add'}
                  </button>
                  <button type="button" className="btn btnGhost" onClick={() => setShowProjectConsultantForm(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {!projectConsultantLoading && !projectConsultantError && availableProjectConsultants.length === 0 ? (
              <span className="muted">All allowed consultants and managers are already associated with this project.</span>
            ) : null}
          </div>
        </section>
      ) : null}

      {showStaffList && (isAdmin || isManager) ? (
        <section className="sectionCard">
          <div className="sectionHeader">
            <SectionHeading
              icon={staffListIcon}
              title={staffListTitle}
              subtitle={staffListSubtitle}
              badge={staffListCount}
            />
          </div>
          {canFilterStaffList ? (
            <div className="staffListFilter">
              <label className="field">
                <span className="label">Staff type</span>
                <select
                  className="select selectScrollable"
                  value={staffTypeFilter}
                  onChange={(e) => setStaffTypeFilter(e.target.value)}
                >
                  <option value="all">All staff</option>
                  <option value="managers">Managers</option>
                  <option value="consultants">Consultants</option>
                </select>
              </label>
            </div>
          ) : null}
          <div className="tableWrap proTableWrap proTableDesktopOnly" style={{ marginTop: 14 }}>
            <table className="dataTable proTable">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Managed by</th>
                  {!readOnly ? <th aria-label="Actions" /> : null}
                </tr>
              </thead>
              <tbody>
                {displayManagersInStaffList ? managers.map((m) => {
                  const descendants = managerDescendantIds(m.id)
                  const editValue = managerEditValue(m)
                  const originalValue = managerParentValue(m)
                  const saving = updatingManagerId === String(m.id)
                  return (
                    <tr key={m.id}>
                      <td>
                        <strong>{m.fullName}</strong>
                      </td>
                      <td className="monoCell">{m.email}</td>
                      <td><span className="proBadge proBadgeManager">Manager</span></td>
                      <td>
                        {readOnly ? (
                          managerParentLabel(m)
                        ) : isAdmin ? (
                          <>
                            <select
                              className="select"
                              value={editValue}
                              onChange={(e) =>
                                setManagerParentEdits((prev) => ({ ...prev, [String(m.id)]: e.target.value }))
                              }
                              disabled={saving}
                            >
                              <option value="">No superior manager</option>
                              {managers
                                .filter((candidate) => {
                                  const candidateId = String(candidate.id ?? '')
                                  return candidateId !== String(m.id) && !descendants.has(candidateId) && isTopLevelManager(candidateId)
                                })
                                .map((candidate) => (
                                  <option key={candidate.id} value={candidate.id}>
                                    {candidate.fullName ?? candidate.email}
                                  </option>
                                ))}
                            </select>
                            <span className="fieldHint">Only top-level managers can be selected.</span>
                          </>
                        ) : (
                          m.managerName ?? '—'
                        )}
                      </td>
                      {!readOnly && isAdmin ? (
                        <td className="cellActions">
                          <button
                            type="button"
                            className="btn btnPrimary btnSm btnWithIcon"
                            disabled={saving || editValue === originalValue}
                            onClick={() => onUpdateManagerParent(m)}
                          >
                            <BtnIcon icon={Pencil} />
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                        </td>
                      ) : !readOnly ? (
                        <td className="cellActions">—</td>
                      ) : (
                        null
                      )}
                    </tr>
                  )
                }) : null}
                {displayConsultantsInStaffList ? consultants.map((c) => (
                  <tr key={`consultant-${c.id}`}>
                    <td><strong>{c.fullName}</strong></td>
                    <td className="monoCell">{c.email}</td>
                    <td><span className="proBadge proBadgeConsultant">Consultant</span></td>
                    <td>{c.managerName ?? '—'}</td>
                    {!readOnly ? (
                      <td className="cellActions">
                        <button
                          type="button"
                          className="btn btnDanger btnSm btnWithIcon"
                          onClick={() => requestRemoveConsultant(c)}
                          disabled={deletingConsultantId === String(c.id)}
                          aria-label={`Delete consultant ${c.fullName ?? c.email ?? ''}`}
                        >
                          <BtnIcon icon={Trash2} />
                          {deletingConsultantId === String(c.id) ? 'Removing...' : 'Delete'}
                        </button>
                      </td>
                    ) : null}
                  </tr>
                )) : null}
              </tbody>
            </table>
            {staffListCount === 0 ? <div className="proEmptyState">No staff users yet.</div> : null}
          </div>

          <div className="proMobileList" style={{ marginTop: 14 }}>
            {staffListCount === 0 ? (
              <div className="proEmptyState">No staff users yet.</div>
            ) : (
              <>
                {displayManagersInStaffList
                  ? managers.map((m) => (
                      <article key={`mm-${m.id}`} className="proMobileCard">
                        <div>
                          <strong>{m.fullName}</strong>
                          <div className="tinyNote monoCell">{m.email}</div>
                        </div>
                        <div>
                          <span className="proMobileLabel">Role</span>
                          <span className="proBadge proBadgeManager">Manager</span>
                        </div>
                        <div>
                          <span className="proMobileLabel">Managed by</span>
                          {managerParentLabel(m)}
                        </div>
                      </article>
                    ))
                  : null}
                {displayConsultantsInStaffList
                  ? consultants.map((c) => (
                      <article key={`mc-${c.id}`} className="proMobileCard">
                        <div>
                          <strong>{c.fullName}</strong>
                          <div className="tinyNote monoCell">{c.email}</div>
                        </div>
                        <div>
                          <span className="proMobileLabel">Role</span>
                          <span className="proBadge proBadgeConsultant">Consultant</span>
                        </div>
                        <div>
                          <span className="proMobileLabel">Managed by</span>
                          {c.managerName ?? '—'}
                        </div>
                        {!readOnly ? (
                          <button
                            type="button"
                            className="btn btnDanger btnSm btnWithIcon"
                            onClick={() => requestRemoveConsultant(c)}
                            disabled={deletingConsultantId === String(c.id)}
                            aria-label={`Delete consultant ${c.fullName ?? c.email ?? ''}`}
                          >
                            <BtnIcon icon={Trash2} />
                            {deletingConsultantId === String(c.id) ? 'Removing...' : 'Delete'}
                          </button>
                        ) : null}
                      </article>
                    ))
                  : null}
              </>
            )}
          </div>
        </section>
      ) : null}

      {showConsultants ? (
      <section className="sectionCard">
        <div className="sectionHeader">
          <h2 className="sectionTitle">Add consultant</h2>
        </div>
        <p className="muted" style={{ marginTop: 0 }}>
          {isManager
            ? 'Create and remove consultants in your team. You can assign allowed consultants or managers to projects.'
            : 'Create a simple consultant or enable manager permissions for this user.'}
        </p>
        <form className="form" onSubmit={onCreateConsultant}>
          <div className="consultantFormGrid">
            <label className="field">
              <span className="label">Full name</span>
              <input
                className="input"
                value={consName}
                onChange={(e) => setConsName(e.target.value)}
                placeholder="Consultant full name"
                required
                autoComplete="name"
              />
            </label>
            <label className="field">
              <span className="label">Email</span>
              <input
                className="input"
                type="email"
                value={consEmail}
                onChange={(e) => setConsEmail(e.target.value)}
                placeholder="consultant@company.com"
                required
                autoComplete="email"
              />
            </label>
            <label className="field">
              <span className="label">Password</span>
              <input
                className="input"
                type="password"
                value={consPassword}
                onChange={(e) => setConsPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                required
                minLength={8}
                autoComplete="new-password"
              />
            </label>
            {isAdmin ? (
              <div className="field consultantManagerToggle">
                <span className="label">Can be manager</span>
                <label className="plainCheckbox">
                  <input
                    type="checkbox"
                    checked={consCanBeManager}
                    onChange={(e) => {
                      setConsCanBeManager(e.target.checked)
                      setConsManagerId('')
                      setConsSuperiorManagerId('')
                    }}
                  />
                  <span>Enable manager permissions</span>
                </label>
              </div>
            ) : null}
            {isAdmin && !consCanBeManager ? (
              <label className="field">
                <span className="label">Manager</span>
                <select
                  className="select selectScrollable"
                  value={selectedConsultantManagerId}
                  onChange={(e) => setConsManagerId(e.target.value)}
                  required
                >
                  {managers.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.fullName} ({m.email})
                    </option>
                  ))}
                </select>
                <span className="fieldHint">The consultant will be managed by this manager.</span>
              </label>
            ) : null}
            {isAdmin && consCanBeManager ? (
              <label className="field">
                <span className="label">Superior manager</span>
                <select
                  className="select"
                  value={consSuperiorManagerId}
                  onChange={(e) => setConsSuperiorManagerId(e.target.value)}
                >
                  <option value="">No superior manager</option>
                  {managers.filter((m) => isTopLevelManager(m.id)).map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.fullName ?? m.email}
                    </option>
                  ))}
                </select>
                <span className="fieldHint">Only top-level managers can be selected.</span>
              </label>
            ) : null}
          </div>
          <div className="formActions">
            <button
              type="submit"
              className="btn btnPrimary"
              disabled={creatingConsultant || (isAdmin && !consCanBeManager && managers.length === 0)}
            >
              {creatingConsultant ? 'Creating...' : consCanBeManager ? 'Create manager' : 'Create consultant'}
            </button>
          </div>
        </form>
        {isAdmin && !consCanBeManager && managers.length === 0 ? (
          <p className="muted">Enable "Can be manager" to create the first manager before adding simple consultants.</p>
        ) : null}
      </section>
      ) : null}

      {showClientAssignment && (isAdmin || isManager) ? (
      <section className="sectionCard">
        <div className="sectionHeader">
          <SectionHeading
            icon={UserPlus}
            title="Assign Consultant"
            subtitle="Only projects with at least one submitted assessment appear in this list (same list as in the Assessments tab). Pick a consultant or manager from your allowed scope."
          />
        </div>
        <form className="form" onSubmit={onAssign}>
          <div className="fieldRow">
            <label className="field">
              <span className="label">Client</span>
              <select
                className="select selectScrollable"
                value={selectedAssignClientId}
                onChange={(e) => setAssignClientId(e.target.value)}
                required
              >
                {clients.map((cl) => (
                  <option key={cl.id} value={cl.id}>
                    {cl.fullName ?? cl.email} — current: {currentProjectAssigneesLabel(cl)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="label">Consultant / Manager</span>
              <select
                className="select selectScrollable"
                value={selectedAssignConsultantId}
                onChange={(e) => setAssignConsultantId(e.target.value)}
                required
                disabled={assignableLoading || assignableAssignees.length === 0}
              >
                {assignableAssignees.map((co) => (
                  <option key={co.id} value={co.id}>
                    {assigneeLabel(co)} ({co.email})
                  </option>
                ))}
              </select>
              {assignableLoading ? <span className="fieldHint">Loading assignable people...</span> : null}
              {!assignableLoading && assignableAssignees.length === 0 ? (
                <span className="fieldHint">No available consultant or manager for this project.</span>
              ) : null}
            </label>
          </div>
          {assignableError ? <div className="alert alertError">{assignableError}</div> : null}
          <button
            type="submit"
            className="btn btnPrimary btnWithIcon"
            style={{ width: 'fit-content' }}
            disabled={assigningConsultant || clients.length === 0 || assignableLoading || assignableAssignees.length === 0}
          >
            <BtnIcon icon={UserPlus} />
            {assigningConsultant ? 'Saving...' : 'Assign'}
          </button>
          {clients.length === 0 ? (
            <p className="muted">No eligible clients yet (submit an assessment first).</p>
          ) : null}
        </form>
      </section>
      ) : null}
    </div>
  )
}
