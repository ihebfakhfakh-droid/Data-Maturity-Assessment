/** Built-in frameworks (backend enum). Custom definitions come from /api/admin/maturity-frameworks. */
export const DEFAULT_FRAMEWORK_OPTIONS = [
  { key: 'NDI', value: 'NDI', code: 'NDI', label: 'NDI', id: null, builtIn: true },
  { key: 'CMMI', value: 'CMMI', code: 'CMMI', label: 'CMMI', id: null, builtIn: true },
]

const FRAMEWORK_COLLECTION_FIELDS = [
  'frameworks',
  'allowedFrameworks',
  'assignedFrameworks',
  'clientFrameworks',
  'evaluationFrameworks',
  'frameworkCodes',
  'frameworkNames',
  'selectedFrameworks',
  'projectFrameworks',
]

const FRAMEWORK_SINGLE_FIELDS = [
  'framework',
  'frameworkCode',
  'frameworkId',
  'frameworkName',
  'frameworkKey',
  'selectedFramework',
]

const FRAMEWORK_OBJECT_CONTAINER_FIELDS = [
  'assessment',
  'client',
  'customer',
  'data',
  'detail',
  'payload',
  'result',
  'item',
  'response',
  'body',
  'project',
  'activeProject',
  'currentProject',
  'questionnaire',
]

const FRAMEWORK_ARRAY_CONTAINER_FIELDS = [
  'assessments',
  'content',
  'domains',
  'items',
  'projects',
  'segments',
  'versions',
]

function text(value) {
  const next = String(value ?? '').trim()
  return next.length > 0 ? next : ''
}

export function frameworkIdentity(value) {
  if (value == null) return ''
  const raw =
    typeof value === 'object'
      ? text(
          value.code ??
            value.frameworkCode ??
            value.key ??
            value.slug ??
            value.name ??
            value.frameworkName ??
            value.label ??
            value.title ??
            value.value ??
            value.id,
        )
      : text(value)

  const normalized = raw.toUpperCase().replaceAll(/[\s-]+/g, '_')
  if (normalized === 'CMMI_DMM') return 'CMMI'
  return normalized
}

export function normalizeFrameworkOption(raw) {
  if (raw == null) return null

  if (typeof raw !== 'object') {
    const value = text(raw)
    if (!value) return null
    return { key: frameworkIdentity(value), value, code: value, label: value, id: null }
  }

  const nested =
    (raw.framework && typeof raw.framework === 'object' ? raw.framework : null) ??
    (raw.evaluationFramework && typeof raw.evaluationFramework === 'object' ? raw.evaluationFramework : null) ??
    (raw.frameworkDto && typeof raw.frameworkDto === 'object' ? raw.frameworkDto : null) ??
    (raw.selectedFramework && typeof raw.selectedFramework === 'object' ? raw.selectedFramework : null)
  const id = raw.frameworkId ?? nested?.id ?? raw.id ?? null
  const code = text(
    raw.code ??
      raw.frameworkCode ??
      raw.key ??
      raw.slug ??
      raw.value ??
      nested?.code ??
      nested?.frameworkCode ??
      nested?.key ??
      nested?.slug ??
      nested?.value,
  )
  const label = text(
    raw.frameworkName ??
      raw.label ??
      raw.title ??
      raw.name ??
      nested?.frameworkName ??
      nested?.label ??
      nested?.title ??
      nested?.name ??
      code ??
      id,
  )
  const value = code || label || text(id)
  const key = frameworkIdentity(code || label || id)

  if (!key || !value) return null
  return { key, value, code: code || value, label: label || value, id }
}

export function frameworkAliases(option) {
  if (!option) return []
  const values = [option.key, option.value, option.code, option.label, option.id]
  return values.map(frameworkIdentity).filter(Boolean)
}

export function uniqueFrameworkOptions(rawOptions) {
  const result = []
  const seen = new Set()

  for (const raw of rawOptions ?? []) {
    const option = normalizeFrameworkOption(raw)
    if (!option) continue

    const aliases = frameworkAliases(option)
    if (aliases.some((alias) => seen.has(alias))) continue

    result.push(option)
    aliases.forEach((alias) => seen.add(alias))
  }

  return result
}

function frameworkRowsFromResponse(data, depth = 0) {
  if (Array.isArray(data)) return data
  if (!data || typeof data !== 'object' || depth > 4) return []

  for (const field of [
    'frameworks',
    'assignedFrameworks',
    'clientFrameworks',
    'evaluationFrameworks',
    'projectFrameworks',
    'selectedFrameworks',
    'items',
    'content',
    'records',
    'list',
  ]) {
    if (Array.isArray(data[field])) return data[field]
  }

  for (const field of ['data', 'payload', 'result', 'response', 'body']) {
    const rows = frameworkRowsFromResponse(data[field], depth + 1)
    if (rows.length > 0) return rows
  }

  return []
}

export function frameworkOptionsFromResponse(data) {
  return uniqueFrameworkOptions(frameworkRowsFromResponse(data))
}

function projectLike(source) {
  if (!source || typeof source !== 'object') return null
  if (source.project && typeof source.project === 'object') return source.project
  if (source.activeProject && typeof source.activeProject === 'object') return source.activeProject
  if (source.currentProject && typeof source.currentProject === 'object') return source.currentProject
  if (!Array.isArray(source.projects)) return null

  return (
    source.projects.find((p) => p?.active || p?.current || p?.latest) ??
    (source.projects.length === 1 ? source.projects[0] : null)
  )
}

export function extractProjectId(client) {
  const project = projectLike(client)
  return (
    client?.projectId ??
    client?.clientProjectId ??
    client?.activeProjectId ??
    client?.currentProjectId ??
    project?.id ??
    project?.projectId ??
    null
  )
}

export function extractAssignedFrameworks(source) {
  if (Array.isArray(source)) {
    return uniqueFrameworkOptions(source.flatMap((item) => extractAssignedFrameworks(item)))
  }

  if (!source || typeof source !== 'object') return []

  const raw = []
  for (const field of FRAMEWORK_COLLECTION_FIELDS) {
    if (Array.isArray(source[field])) raw.push(...source[field])
  }
  if (Array.isArray(source.frameworkIds)) {
    raw.push(...source.frameworkIds.map((id) => ({ id, frameworkId: id })))
  }
  for (const field of FRAMEWORK_SINGLE_FIELDS) {
    if (source[field] != null) raw.push(source[field])
  }

  for (const field of FRAMEWORK_OBJECT_CONTAINER_FIELDS) {
    if (source[field] && typeof source[field] === 'object') {
      raw.push(...extractAssignedFrameworks(source[field]))
    }
  }
  for (const field of FRAMEWORK_ARRAY_CONTAINER_FIELDS) {
    if (Array.isArray(source[field])) {
      raw.push(...extractAssignedFrameworks(source[field]))
    }
  }

  const project = projectLike(source)
  if (project && project !== source) {
    raw.push(...extractAssignedFrameworks(project))
  }

  return uniqueFrameworkOptions(raw)
}

export function hasFramework(assignedFrameworks, option) {
  const assignedAliases = new Set((assignedFrameworks ?? []).flatMap(frameworkAliases))
  return frameworkAliases(option).some((alias) => assignedAliases.has(alias))
}

export function formatClientLabel(client) {
  return String(client?.fullName ?? client?.email ?? `Client ${client?.id ?? ''}`).trim()
}
