import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../../api/client.js'
import { loadFrameworkCatalog } from '../../api/frameworkApi.js'
import {
  DEFAULT_FRAMEWORK_OPTIONS,
  extractAssignedFrameworks,
  extractProjectId,
  formatClientLabel,
  frameworkAliases,
  frameworkOptionsFromResponse,
  hasFramework,
  uniqueFrameworkOptions,
} from './frameworkUtils.js'

function numericOrString(value) {
  const asNumber = Number(value)
  return Number.isFinite(asNumber) && String(value).trim() !== '' ? asNumber : value
}

function clientFrameworksPath(clientId) {
  return `/api/admin/clients/${clientId}/frameworks`
}

function frameworksFromAssignmentResponse(data) {
  const directOptions = frameworkOptionsFromResponse(data)
  return uniqueFrameworkOptions([...extractAssignedFrameworks(data), ...directOptions])
}

function resolveFrameworkLabels(options, catalog) {
  return uniqueFrameworkOptions(
    (options ?? []).map((option) => {
      const normalized = uniqueFrameworkOptions([option])[0]
      if (!normalized) return option

      const catalogMatch = (catalog ?? []).find(
        (catalogOption) => hasFramework([normalized], catalogOption) || hasFramework([catalogOption], normalized),
      )

      return catalogMatch ? { ...catalogMatch, id: normalized.id ?? catalogMatch.id } : normalized
    }),
  )
}

function collectionFromResponse(data, fields = []) {
  if (Array.isArray(data)) return data
  if (!data || typeof data !== 'object') return []

  for (const field of fields) {
    if (Array.isArray(data[field])) return data[field]
  }
  for (const field of ['items', 'content', 'records', 'projects', 'data', 'payload']) {
    if (Array.isArray(data[field])) return data[field]
  }

  return []
}

function valueMatchesId(value, id) {
  return value != null && String(value) === String(id)
}

function projectBelongsToClient(project, clientId) {
  if (!project || typeof project !== 'object') return false
  return (
    valueMatchesId(project.clientId, clientId) ||
    valueMatchesId(project.client_id, clientId) ||
    valueMatchesId(project.customerId, clientId) ||
    valueMatchesId(project.customer_id, clientId) ||
    valueMatchesId(project.client?.id, clientId) ||
    valueMatchesId(project.customer?.id, clientId)
  )
}

function projectIdFromProject(project) {
  return project?.id ?? project?.projectId ?? project?.project_id ?? null
}

async function fetchProjectFrameworks(projectId, options) {
  if (projectId == null || projectId === '') return []

  const candidates = [
    `/api/admin/projects/${projectId}/frameworks`,
    `/api/admin/projects/${projectId}`,
  ]
  const collected = []

  for (const path of candidates) {
    try {
      const data = await apiFetch(path, {
        ...(options ?? {}),
        method: 'GET',
      })
      collected.push(...frameworksFromAssignmentResponse(data))
    } catch {
      // Optional project endpoints vary by backend implementation.
    }
  }

  return uniqueFrameworkOptions(collected)
}

async function fetchFrameworksFromClientProjects(clientId, options) {
  const candidates = [
    { path: `/api/admin/clients/${clientId}/project`, fields: ['project'], single: true },
    { path: `/api/admin/clients/${clientId}/projects`, fields: ['projects'] },
    { path: `/api/admin/projects?clientId=${encodeURIComponent(String(clientId))}`, fields: ['projects'] },
    { path: '/api/admin/projects', fields: ['projects'], filterByClient: true },
  ]
  const projectRows = []
  const collected = []

  for (const candidate of candidates) {
    try {
      const data = await apiFetch(candidate.path, {
        ...(options ?? {}),
        method: 'GET',
      })
      const rows = candidate.single ? [data?.project ?? data].filter(Boolean) : collectionFromResponse(data, candidate.fields)
      const scopedRows = candidate.filterByClient ? rows.filter((row) => projectBelongsToClient(row, clientId)) : rows
      projectRows.push(...scopedRows)
      collected.push(...scopedRows.flatMap((row) => extractAssignedFrameworks(row)))
    } catch {
      // Optional project lookup endpoints vary by backend implementation.
    }
  }

  const projectIds = [...new Set(projectRows.map(projectIdFromProject).filter((id) => id != null && id !== ''))]
  const projectFrameworks = await Promise.all(projectIds.map((projectId) => fetchProjectFrameworks(projectId, options)))

  return uniqueFrameworkOptions([...collected, ...projectFrameworks.flat()])
}

async function fetchAssignedFrameworks(clientId, options) {
  let clientError = null

  try {
    const clientResponse = await apiFetch(clientFrameworksPath(clientId), {
      ...(options ?? {}),
      method: 'GET',
    })
    const frameworks = frameworksFromAssignmentResponse(clientResponse)
    if (frameworks.length > 0) return frameworks
  } catch (err) {
    clientError = err
  }

  const projectFrameworks = await fetchFrameworksFromClientProjects(clientId, options)
  if (projectFrameworks.length > 0) return projectFrameworks

  if (clientError) throw clientError

  return []
}

async function addFrameworkToClient(clientId, options) {
  const data = await apiFetch(clientFrameworksPath(clientId), {
    ...(options ?? {}),
    method: 'POST',
  })
  return frameworksFromAssignmentResponse(data)
}

export function ProjectFrameworkManager({
  token,
  clients,
  selectedClientId,
  onClientsRefresh,
  title = 'Add Framework',
  description = 'Add an available framework to an existing client project without removing already assigned frameworks.',
  sharedFrameworkCatalog,
  sharedFrameworkCatalogLoading = false,
  sharedFrameworkCatalogError = '',
  onRetryFrameworkCatalog,
}) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token])
  const usesSharedFrameworkCatalog = Array.isArray(sharedFrameworkCatalog)
  const [localFrameworkCatalog, setLocalFrameworkCatalog] = useState(DEFAULT_FRAMEWORK_OPTIONS)
  const [localFrameworkCatalogError, setLocalFrameworkCatalogError] = useState('')
  const [localLoadingFrameworks, setLocalLoadingFrameworks] = useState(false)
  const frameworkCatalog = usesSharedFrameworkCatalog
    ? sharedFrameworkCatalog.length
      ? sharedFrameworkCatalog
      : DEFAULT_FRAMEWORK_OPTIONS
    : localFrameworkCatalog
  const frameworkCatalogError = usesSharedFrameworkCatalog
    ? sharedFrameworkCatalogError ?? ''
    : localFrameworkCatalogError
  const loadingFrameworks = usesSharedFrameworkCatalog
    ? Boolean(sharedFrameworkCatalogLoading)
    : localLoadingFrameworks
  const [clientId, setClientId] = useState(selectedClientId ? String(selectedClientId) : '')
  const [frameworkKey, setFrameworkKey] = useState('')
  const [remoteAssignments, setRemoteAssignments] = useState({})
  const [localAssignments, setLocalAssignments] = useState({})
  const [loadingAssignments, setLoadingAssignments] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const refreshFrameworkCatalog = useCallback(async () => {
    if (usesSharedFrameworkCatalog) {
      onRetryFrameworkCatalog?.()
      return
    }
    setLocalLoadingFrameworks(true)
    const catalog = await loadFrameworkCatalog(token, { force: true })
    setLocalFrameworkCatalog(catalog.options.length ? catalog.options : DEFAULT_FRAMEWORK_OPTIONS)
    setLocalFrameworkCatalogError(catalog.error ?? '')
    setLocalLoadingFrameworks(false)
  }, [token, usesSharedFrameworkCatalog, onRetryFrameworkCatalog])

  useEffect(() => {
    if (usesSharedFrameworkCatalog) return undefined
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshFrameworkCatalog()
    return undefined
  }, [refreshFrameworkCatalog, usesSharedFrameworkCatalog])

  const effectiveClientId =
    selectedClientId != null ? String(selectedClientId) : clientId || (clients?.[0]?.id != null ? String(clients[0].id) : '')

  const selectedClient = useMemo(
    () => (clients ?? []).find((client) => String(client.id) === String(effectiveClientId)) ?? null,
    [clients, effectiveClientId],
  )

  useEffect(() => {
    if (!selectedClient) return undefined

    let cancelled = false
    const id = String(selectedClient.id)
    const clientFrameworks = extractAssignedFrameworks(selectedClient)

    async function run() {
      setLoadingAssignments(true)
      try {
        const fetchedFrameworks = await fetchAssignedFrameworks(selectedClient.id, { headers })
        if (!cancelled) {
          setRemoteAssignments((prev) => ({
            ...prev,
            [id]: uniqueFrameworkOptions([...clientFrameworks, ...fetchedFrameworks]),
          }))
        }
      } catch (err) {
        if (!cancelled) {
          setRemoteAssignments((prev) => ({
            ...prev,
            [id]: clientFrameworks,
          }))
          setError(err?.message ?? 'Could not load client frameworks')
        }
      } finally {
        if (!cancelled) setLoadingAssignments(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [headers, selectedClient])

  const rawAssignedFrameworks = useMemo(() => {
    if (!selectedClient) return []
    return uniqueFrameworkOptions([
      ...extractAssignedFrameworks(selectedClient),
      ...(remoteAssignments[String(selectedClient.id)] ?? []),
      ...(localAssignments[String(selectedClient.id)] ?? []),
    ])
  }, [localAssignments, remoteAssignments, selectedClient])

  const assignedFrameworks = useMemo(
    () => resolveFrameworkLabels(rawAssignedFrameworks, frameworkCatalog),
    [frameworkCatalog, rawAssignedFrameworks],
  )

  const frameworkOptions = useMemo(
    () => uniqueFrameworkOptions([...frameworkCatalog, ...assignedFrameworks]),
    [assignedFrameworks, frameworkCatalog],
  )

  const availableFrameworks = useMemo(
    () => frameworkOptions.filter((option) => !hasFramework(assignedFrameworks, option)),
    [assignedFrameworks, frameworkOptions],
  )

  const effectiveFrameworkKey = availableFrameworks.some((option) => option.key === frameworkKey)
    ? frameworkKey
    : availableFrameworks[0]?.key ?? ''

  async function onAddFramework(e) {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!selectedClient) {
      setError('Select a client first.')
      return
    }

    const option = availableFrameworks.find((item) => item.key === effectiveFrameworkKey)
    if (!option) {
      setError('No framework is available for this project.')
      return
    }

    if (hasFramework(assignedFrameworks, option)) {
      setError('This framework is already assigned to the project.')
      return
    }

    const projectId = extractProjectId(selectedClient)
    const body = JSON.stringify({
      clientId: numericOrString(selectedClient.id),
      ...(projectId != null ? { projectId: numericOrString(projectId) } : {}),
      ...(option.id != null && !option.builtIn
        ? { customMaturityFrameworkIds: [numericOrString(option.id)], frameworkId: numericOrString(option.id) }
        : {
            frameworks: [option.value],
            framework: option.value,
            frameworkCode: option.code,
            frameworkName: option.label,
          }),
    })

    setSubmitting(true)
    try {
      const latestAssigned = await fetchAssignedFrameworks(selectedClient.id, { headers })
      const latestWithLocal = uniqueFrameworkOptions([...assignedFrameworks, ...latestAssigned])

      if (hasFramework(latestWithLocal, option)) {
        setRemoteAssignments((prev) => ({
          ...prev,
          [String(selectedClient.id)]: latestWithLocal,
        }))
        setError('This framework is already assigned to the project.')
        return
      }

      const responseFrameworks = await addFrameworkToClient(selectedClient.id, { headers, body })
      const refreshedFrameworks = await fetchAssignedFrameworks(selectedClient.id, { headers }).catch(() => [])
      const nextAssigned = uniqueFrameworkOptions([
        ...latestWithLocal,
        ...responseFrameworks,
        ...refreshedFrameworks,
        option,
      ])

      setLocalAssignments((prev) => ({
        ...prev,
        [String(selectedClient.id)]: nextAssigned,
      }))
      setRemoteAssignments((prev) => ({
        ...prev,
        [String(selectedClient.id)]: nextAssigned,
      }))
      const nextAvailable = frameworkOptions.filter((item) => !hasFramework(nextAssigned, item))
      setFrameworkKey(nextAvailable[0]?.key ?? '')
      setSuccess(`${option.label} added to ${formatClientLabel(selectedClient)}.`)
      await onClientsRefresh?.()
    } catch (err) {
      setError(err?.message ?? 'Could not add framework')
    } finally {
      setSubmitting(false)
    }
  }

  const assignedAliases = new Set(assignedFrameworks.flatMap(frameworkAliases))

  return (
    <section className="sectionCard">
      <div className="sectionHeader">
        <div>
          <h2 className="sectionTitle">{title}</h2>
          <p className="sectionHint">{description}</p>
        </div>
        <div className="badge">{assignedFrameworks.length}</div>
      </div>

      {error ? <div className="alert alertError">{error}</div> : null}
      {frameworkCatalogError ? (
        <div className="alert alertError">
          {frameworkCatalogError}
          <div style={{ marginTop: 8 }}>
            <button type="button" className="btn btnGhost btnSm" onClick={refreshFrameworkCatalog}>
              Retry
            </button>
          </div>
        </div>
      ) : null}
      {success ? <div className="alert alertSuccess">{success}</div> : null}

      <form className="form" onSubmit={onAddFramework}>
        <div className="fieldRow">
          <label className="field">
            <span className="label">Client</span>
            {selectedClientId != null ? (
              <div className="input" style={{ display: 'flex', alignItems: 'center' }}>
                {selectedClient ? formatClientLabel(selectedClient) : 'No client selected'}
              </div>
            ) : (
              <select
                className="select selectScrollable"
                value={effectiveClientId}
                onChange={(e) => {
                  setClientId(e.target.value)
                  setFrameworkKey('')
                  setError('')
                  setSuccess('')
                }}
                required
              >
                {(clients ?? []).map((client) => (
                  <option key={client.id} value={client.id}>
                    {formatClientLabel(client)}
                  </option>
                ))}
              </select>
            )}
          </label>

          <label className="field">
            <span className="label">Available framework</span>
            <select
              className="select selectScrollable"
              value={loadingAssignments ? '' : effectiveFrameworkKey}
              onChange={(e) => setFrameworkKey(e.target.value)}
              disabled={availableFrameworks.length === 0 || loadingFrameworks || loadingAssignments}
              required
            >
              {loadingAssignments ? (
                <option value="">Loading current frameworks...</option>
              ) : (
                availableFrameworks.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))
              )}
            </select>
          </label>
        </div>

        <div style={{ display: 'grid', gap: 8 }}>
          <div className="muted">Current frameworks</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {assignedFrameworks.length > 0 ? (
              assignedFrameworks.map((option) => (
                <span key={option.key} className="badge">
                  {option.label}
                </span>
              ))
            ) : loadingAssignments ? (
              <span className="muted">Loading current frameworks...</span>
            ) : (
              <span className="muted">No framework detected for this project yet.</span>
            )}
          </div>
          {availableFrameworks.length === 0 && selectedClient && !loadingAssignments ? (
            <div className="muted">
              {assignedAliases.size > 0
                ? 'All available frameworks are already assigned.'
                : 'No framework catalog is available.'}
            </div>
          ) : null}
        </div>

        <button
          type="submit"
          className="btn btnPrimary"
          style={{ width: 'fit-content' }}
          disabled={!selectedClient || availableFrameworks.length === 0 || submitting || loadingFrameworks || loadingAssignments}
        >
          {submitting ? 'Adding...' : 'Add Framework'}
        </button>
      </form>
    </section>
  )
}
