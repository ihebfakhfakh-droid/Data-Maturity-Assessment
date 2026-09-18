import { useCallback, useEffect, useState } from 'react'
import {
  ArrowLeft,
  BarChart3,
  BriefcaseBusiness,
  ChevronDown,
  CircleCheck,
  ClipboardCheck,
  ClipboardList,
  Eye,
  FileDown,
  FolderKanban,
  History,
  Layers3,
  Menu,
  Pencil,
  RefreshCw,
  Users,
  UsersRound,
  X,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { apiFetch, apiFetchFormData } from '../../api/client.js'
import { useAuth } from '../../auth/AuthProvider.jsx'
import {
  canManageStaffTeam,
  isAdminRole,
  isStaffRole,
  roleFromAuth,
  staffAssessmentEditPathForRole,
} from '../../auth/roles.js'
import { BtnIcon, SectionHeading } from '../../ui/IconBox.jsx'
import { exportAssessmentPdf, isSubmittedAssessment } from '../../utils/assessmentPdf.js'
import { buildAdminAssessmentPdfReport } from './assessmentPdfReport.js'
import { AddFrameworkPanel } from './AddFrameworkPanel.jsx'
import { AssessmentDetailsDomains, evidenceItemsForAnswer, maturityLabelEn } from './AssessmentDetailsDomains.jsx'
import { AssessmentVersioningOverlay } from './AssessmentVersioningOverlay.jsx'
import { RecommendationActionsPanel } from './RecommendationActionsPanel.jsx'
import { downloadAcceptanceCriteriaReport } from '../../api/acceptanceCriteriaApi.js'
import { deleteEvidence } from '../../api/evidenceApi.js'
import {
  assessmentVersionDetailPath,
  assessmentVersionsListPath,
  markLatestVersion,
  normalizeVersionDetail,
  normalizeVersionRow,
} from './assessmentVersioningApi.js'
import { BUILT_IN_FRAMEWORK_OPTIONS, loadFrameworkCatalog } from '../../api/frameworkApi.js'
import { DEFAULT_FRAMEWORK_OPTIONS } from './frameworkUtils.js'
import { ManagerDashboardView } from './ManagerDashboardView.jsx'
import { StaffTeamPanel } from './StaffTeamPanel.jsx'

function parseVersionsResponse(raw) {
  if (Array.isArray(raw)) return raw
  if (raw?.content && Array.isArray(raw.content)) return raw.content
  if (raw?.items && Array.isArray(raw.items)) return raw.items
  if (raw?.versions && Array.isArray(raw.versions)) return raw.versions
  return []
}

const ASSESSMENT_PROJECT_VIEWS = ['assessment-submitted', 'assessment-draft']

function isAssessmentProjectView(view) {
  return ASSESSMENT_PROJECT_VIEWS.includes(view)
}

function FrameworkCatalogPanel({ frameworks, loading = false, error = '', onRetry }) {
  return (
    <section className="sectionCard">
      <div className="sectionHeader">
        <SectionHeading
          icon={Layers3}
          title="Frameworks"
          subtitle="Built-in frameworks and admin-defined maturity frameworks."
          badge={frameworks.length}
        />
      </div>
      {error ? (
        <div className="alert alertError" style={{ marginBottom: 12 }}>
          {error}
          {typeof onRetry === 'function' ? (
            <div style={{ marginTop: 8 }}>
              <button type="button" className="btn btnGhost btnSm btnWithIcon" onClick={onRetry}>
                <BtnIcon icon={RefreshCw} />
                Retry
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {loading ? <p className="muted">Loading frameworks…</p> : null}
      {!loading && frameworks.length === 0 && !error ? (
        <p className="muted">No frameworks available.</p>
      ) : null}
      {!loading && frameworks.length > 0 ? (
        <div className="tableWrap">
          <table className="dataTable">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {frameworks.map((framework) => (
                <tr key={framework.key ?? framework.code ?? framework.value ?? framework.label}>
                  <td className="monoCell">{framework.code || framework.value}</td>
                  <td>
                    <strong>{framework.label ?? framework.value ?? framework.key}</strong>
                  </td>
                  <td>{framework.builtIn ? 'Built-in' : 'Custom'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}

export function AdminDashboardPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const role = roleFromAuth(auth)
  const isStaff = isStaffRole(role)
  const showTeamTab = canManageStaffTeam(role)
  const isAdmin = isAdminRole(role)
  const isConsultant = role === 'CONSULTANT'
  const isManager = role === 'MANAGER'
  const canUseAiRecommendations = isConsultant || isManager
  const canOpenAssessmentVersions = isStaff && !isAdmin

  const [staffTab, setStaffTab] = useState(isConsultant ? 'projects' : 'dashboard')
  const [openStaffMenu, setOpenStaffMenu] = useState(isConsultant ? '' : 'dashboard')
  const [staffSubView, setStaffSubView] = useState(isConsultant ? 'project-existing' : 'overview')
  const [projectAssessmentsOpen, setProjectAssessmentsOpen] = useState(false)
  const [projectNewOpen, setProjectNewOpen] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [clients, setClients] = useState([])
  const [selectedClientId, setSelectedClientId] = useState(null)
  const [assessments, setAssessments] = useState([])
  const [allAssessments, setAllAssessments] = useState([])
  const [selectedAssessmentId, setSelectedAssessmentId] = useState(null)
  const [assessment, setAssessment] = useState(null)
  const [assessmentStep, setAssessmentStep] = useState('clients')
  const [assessmentVersions, setAssessmentVersions] = useState([])
  const [assessmentVersionsLoading, setAssessmentVersionsLoading] = useState(false)
  const [assessmentVersionsError, setAssessmentVersionsError] = useState('')
  const [versionOverlayClient, setVersionOverlayClient] = useState(null)
  const [assessmentDetailBackStep, setAssessmentDetailBackStep] = useState('versions')
  const [detailClient, setDetailClient] = useState(null)
  const [assessmentFilters, setAssessmentFilters] = useState({
    client: '',
  })
  const [assessmentClientMenuOpen, setAssessmentClientMenuOpen] = useState(false)
  const [assessmentClientSearch, setAssessmentClientSearch] = useState('')
  const [dashboardStats, setDashboardStats] = useState({
    projectCount: 0,
    assessmentCount: 0,
    managerCount: 0,
    consultantCount: 0,
    frameworkCount: DEFAULT_FRAMEWORK_OPTIONS.length,
    draftAssessmentCount: 0,
    submittedAssessmentCount: 0,
  })
  const [frameworkCatalog, setFrameworkCatalog] = useState(DEFAULT_FRAMEWORK_OPTIONS)
  const [frameworkCatalogError, setFrameworkCatalogError] = useState('')
  const [frameworkCatalogLoading, setFrameworkCatalogLoading] = useState(false)
  const [frameworkCatalogTick, setFrameworkCatalogTick] = useState(0)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [dashboardProjects, setDashboardProjects] = useState([])
  const [dashboardConsultants, setDashboardConsultants] = useState([])
  const [dashboardManagers, setDashboardManagers] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)

  // Evidence confidence (staff rating): LOW / MEDIUM / HIGH

  useEffect(() => {
    console.log('[AdminDashboardPage] resolved role for Export Assessment Report', {
      authRole: auth.role,
      storedRole: localStorage.getItem('pfe.auth.role'),
      role,
      isStaff,
    })
  }, [auth.role, role, isStaff])

  async function rateEvidence(evidenceId, rating) {
    await apiFetch(`/api/admin/evidences/${evidenceId}/rating`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: JSON.stringify({ rating, comment: '' }),
    })
    setAssessment((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        segments: (prev.segments ?? []).map((seg) => ({
          ...seg,
          answers: (seg.answers ?? []).map((ans) =>
            evidenceItemsForAnswer(ans).some((item) => String(item.id) === String(evidenceId))
              ? { ...ans, evidenceStaffRating: rating }
              : ans,
          ),
          subDomains: (seg.subDomains ?? []).map((sub) => ({
            ...sub,
            answers: (sub.answers ?? []).map((ans) =>
              evidenceItemsForAnswer(ans).some((item) => String(item.id) === String(evidenceId))
                ? { ...ans, evidenceStaffRating: rating }
                : ans,
            ),
          })),
        })),
      }
    })
  }

  async function generateAcceptanceCriteriaReport(evidenceId) {
    setError('')
    setSuccess('')
    try {
      const filename = await downloadAcceptanceCriteriaReport(evidenceId, auth.token)
      setSuccess(`Acceptance Criteria report downloaded${filename ? `: ${filename}` : ''}.`)
    } catch (err) {
      setError(err?.message ?? 'Failed to generate Acceptance Criteria report.')
      throw err
    }
  }

  async function removeEvidence(evidenceId) {
    await deleteEvidence(evidenceId, auth.token, { staff: true })
    setAssessment((prev) => {
      if (!prev) return prev
      const strip = (ans) => {
        const items = evidenceItemsForAnswer(ans).filter((item) => String(item.id) !== String(evidenceId))
        const first = items[0] ?? null
        return {
          ...ans,
          evidences: items,
          evidenceId: first?.id ?? null,
          evidenceFileName: first?.fileName ?? null,
        }
      }
      return {
        ...prev,
        segments: (prev.segments ?? []).map((seg) => ({
          ...seg,
          answers: (seg.answers ?? []).map(strip),
          subDomains: (seg.subDomains ?? []).map((sub) => ({
            ...sub,
            answers: (sub.answers ?? []).map(strip),
          })),
        })),
      }
    })
  }

  async function uploadEvidenceForAnswer(assessmentId, questionCode, score, files) {
    const uploadFiles = Array.from(files ?? []).filter(Boolean)
    if (uploadFiles.length === 0) return
    const form = new FormData()
    form.append('score', String(score ?? 0))
    for (const file of uploadFiles) {
      form.append('file', file)
    }
    await apiFetchFormData(
      `/api/admin/assessments/${assessmentId}/answers/${encodeURIComponent(questionCode)}/evidence`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: form,
      },
    )
    // Refresh full assessment to get evidenceId + fileName in the response.
    const fresh = await apiFetch(`/api/admin/assessments/${assessmentId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    setAssessment(normalizeVersionDetail(fresh) ?? fresh)
  }

  const refreshClients = useCallback(async () => {
    const data = await apiFetch('/api/admin/clients', {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    setClients(data ?? [])
    return data ?? []
  }, [auth.token])

  const refreshClientsAndSelection = useCallback(async () => {
    try {
      const data = await refreshClients()
      const ids = new Set((data ?? []).map((c) => c.id))
      if (selectedClientId != null && !ids.has(selectedClientId)) {
        setSelectedClientId((data ?? [])[0]?.id ?? null)
        setSelectedAssessmentId(null)
        setAssessment(null)
      }
      return data
    } catch (err) {
      setError(err?.message ?? 'Failed to refresh clients')
      return []
    }
  }, [refreshClients, selectedClientId])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setError('')
      try {
        setLoading(true)
        const data = await refreshClients()
        if (cancelled) return
        const first = (data ?? [])[0]?.id ?? null
        setSelectedClientId(first)
        setSelectedAssessmentId(null)
        setAssessment(null)
      } catch (err) {
        if (!cancelled) setError(err?.message ?? 'Failed to load dashboard')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [auth.token, refreshClients])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!selectedClientId) {
        setAssessments([])
        return
      }
      setError('')

      const cachedForClient = (allAssessments ?? []).filter(
        (row) => String(row?.client?.id ?? row?.clientId ?? '') === String(selectedClientId),
      )
      if (cachedForClient.length > 0) {
        setAssessments(cachedForClient)
        return
      }

      try {
        const data = await apiFetch(`/api/admin/clients/${selectedClientId}/assessments`, {
          headers: { Authorization: `Bearer ${auth.token}` },
        })
        if (cancelled) return
        setAssessments(data ?? [])
      } catch (err) {
        if (!cancelled) setError(err?.message ?? 'Failed to load assessments')
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [auth.token, selectedClientId, allAssessments])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!selectedAssessmentId) return
      setError('')
      setAssessment(null)
      try {
        const data = await apiFetch(`/api/admin/assessments/${selectedAssessmentId}`, {
          headers: { Authorization: `Bearer ${auth.token}` },
        })
        if (!cancelled) setAssessment(normalizeVersionDetail(data) ?? data)
      } catch (err) {
        if (!cancelled) setError(err?.message ?? 'Failed to load assessment')
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [auth.token, selectedAssessmentId])

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!selectedClientId || assessmentStep !== 'versions' || !canOpenAssessmentVersions) return
      setAssessmentVersionsLoading(true)
      setAssessmentVersionsError('')
      setAssessmentVersions([])
      try {
        const raw = await apiFetch(assessmentVersionsListPath(selectedClientId), {
          headers: { Authorization: `Bearer ${auth.token}` },
        })
        if (cancelled) return
        const rows = parseVersionsResponse(raw)
        setAssessmentVersions(markLatestVersion(rows.map((version, index) => normalizeVersionRow(version, index))))
      } catch (err) {
        if (!cancelled) setAssessmentVersionsError(err?.message ?? 'Could not load assessment versions')
      } finally {
        if (!cancelled) setAssessmentVersionsLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [assessmentStep, auth.token, canOpenAssessmentVersions, selectedClientId])

  useEffect(() => {
    let cancelled = false
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null

    async function run() {
      setFrameworkCatalogLoading(true)
      try {
        const catalog = await loadFrameworkCatalog(auth.token, {
          signal: controller?.signal,
          includeBuiltIn: true,
          force: frameworkCatalogTick > 0,
        })
        if (cancelled || catalog.aborted) return
        setFrameworkCatalog(catalog.options.length ? catalog.options : BUILT_IN_FRAMEWORK_OPTIONS)
        setFrameworkCatalogError(catalog.error ?? '')
      } finally {
        if (!cancelled) setFrameworkCatalogLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
      controller?.abort()
    }
  }, [auth.token, frameworkCatalogTick])

  const clientIdsKey = clients.map((client) => client.id).join(',')

  useEffect(() => {
    let cancelled = false
    async function run() {
      if (!clients.length) {
        setAllAssessments([])
        setDashboardProjects([])
        setDashboardConsultants([])
        setDashboardManagers([])
        setDashboardStats((prev) => ({
          ...prev,
          projectCount: 0,
          assessmentCount: 0,
          managerCount: 0,
          consultantCount: 0,
          frameworkCount: frameworkCatalog.length || BUILT_IN_FRAMEWORK_OPTIONS.length,
          draftAssessmentCount: 0,
          submittedAssessmentCount: 0,
        }))
        return
      }

      setDashboardLoading(true)
      try {
        const headers = { Authorization: `Bearer ${auth.token}` }
        const [projectRows, assessmentRows, managers, consultants] = await Promise.all([
          Promise.all(
            clients.map((client) =>
              apiFetch(`/api/admin/clients/${client.id}/project`, { headers })
                .then((project) => (project ? project : null))
                .catch(() => null),
            ),
          ),
          Promise.all(
            clients.map((client) =>
              apiFetch(`/api/admin/clients/${client.id}/assessments`, { headers })
                .then((rows) => (Array.isArray(rows) ? rows.map((row) => ({ ...row, client })) : []))
                .catch(() => []),
            ),
          ),
          showTeamTab ? apiFetch('/api/admin/staff/managers', { headers }).catch(() => []) : Promise.resolve([]),
          showTeamTab ? apiFetch('/api/admin/staff/consultants', { headers }).catch(() => []) : Promise.resolve([]),
        ])
        if (cancelled) return
        const nextAssessments = assessmentRows.flat()
        const assessmentStatus = (item) => String(item?.globalStatus ?? item?.status ?? item?.workflowStatus ?? '').toUpperCase()
        const submittedAssessmentCount = nextAssessments.filter((item) => assessmentStatus(item) === 'SUBMITTED').length
        const draftAssessmentCount = nextAssessments.filter((item) => {
          const status = assessmentStatus(item)
          return status === 'DRAFT' || status === 'IN_PROGRESS'
        }).length
        const nextProjects = clients
          .map((client, index) => {
            const project = projectRows[index]
            return project ? { client, project } : null
          })
          .filter(Boolean)
        setAllAssessments(nextAssessments)
        setDashboardProjects(nextProjects)
        setDashboardConsultants(Array.isArray(consultants) ? consultants : [])
        setDashboardManagers(Array.isArray(managers) ? managers : [])
        setDashboardStats({
          projectCount: nextProjects.length,
          assessmentCount: nextAssessments.length,
          managerCount: Array.isArray(managers) ? managers.length : 0,
          consultantCount: Array.isArray(consultants) ? consultants.length : 0,
          frameworkCount: frameworkCatalog.length || BUILT_IN_FRAMEWORK_OPTIONS.length,
          draftAssessmentCount,
          submittedAssessmentCount,
        })
      } finally {
        if (!cancelled) setDashboardLoading(false)
      }
    }

    run()
    return () => {
      cancelled = true
    }
    // clients identity changes often; clientIdsKey is the stable dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.token, clientIdsKey, showTeamTab, frameworkCatalog.length])

  const assessmentDomains = assessment?.segments ?? []
  const frameworkAverages = assessment?.frameworkAverages ?? []
  const frameworkAvg = assessment?.frameworkAvg ?? null
  const frameworkAverageScore = assessment?.frameworkAverageScore ?? assessment?.globalAverageScore ?? null
  const frameworkMaturityLabel = assessment?.frameworkMaturityLabel ?? ''
  const selectedClient = clients.find((client) => client.id === selectedClientId) ?? null
  const detailDisplayClient = detailClient ?? selectedClient
  const selectedAssessmentSummary = assessments.find((item) => item.id === selectedAssessmentId) ?? null
  const assessmentStatusValue = (item) =>
    String(item?.globalStatus ?? item?.status ?? item?.workflowStatus ?? '').toUpperCase()
  const assessmentStatusLabel = (item) => {
    const status = assessmentStatusValue(item)
    if (status === 'SUBMITTED') return 'Submitted'
    if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'Current Assessment'
    return status || '—'
  }
  const frameworkStatusRows = (item) => (Array.isArray(item?.frameworkStatus) ? item.frameworkStatus : [])
  const frameworkStatusLabel = (row) => {
    const status = String(row?.frameworkStatus ?? row?.status ?? '').toUpperCase()
    if (status === 'SUBMITTED') return 'Submitted'
    if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'Current Assessment'
    return status || '—'
  }
  const isFrameworkSubmitted = (row) =>
    String(row?.frameworkStatus ?? row?.status ?? '').toUpperCase() === 'SUBMITTED'
  const formatSubmittedDate = (value) => {
    if (!value) return ''
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return ''
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(date)
  }
  const latestDateValue = (...values) => {
    const dates = values
      .filter(Boolean)
      .map((value) => new Date(value))
      .filter((date) => !Number.isNaN(date.getTime()))
      .sort((a, b) => b.getTime() - a.getTime())
    return dates[0]?.toISOString() ?? ''
  }
  const frameworkSubmittedDate = (row) =>
    latestDateValue(
      row?.lastSubmissionDate,
      row?.lastSubmittedAt,
      row?.frameworkSubmittedAt,
      row?.submittedAt,
      row?.submitted_at,
    )
  const frameworkCodeFromQuestionCode = (questionCode) => {
    const code = String(questionCode ?? '').toLowerCase()
    if (code.startsWith('ndi_')) return 'NDI'
    if (code.startsWith('cmmi_')) return 'CMMI'
    return ''
  }
  const answerDate = (answer) =>
    latestDateValue(
      answer?.lastSubmissionDate,
      answer?.lastSubmittedAt,
      answer?.frameworkSubmittedAt,
      answer?.submittedAt,
      answer?.submitted_at,
      answer?.answeredAt,
      answer?.answered_at,
      answer?.updatedAt,
      answer?.updated_at,
    )
  const latestAnswerDateForFramework = (frameworkCode) => {
    const target = String(frameworkCode ?? '').toUpperCase()
    const dates = []
    const collect = (answers = []) => {
      for (const ans of answers) {
        if (frameworkCodeFromQuestionCode(ans?.questionCode) !== target) continue
        const date = answerDate(ans)
        if (date) dates.push(date)
      }
    }

    for (const seg of assessmentDomains) {
      collect(seg?.answers)
      for (const sub of seg?.subDomains ?? seg?.subdomains ?? []) {
        collect(sub?.answers)
      }
    }
    return latestDateValue(...dates)
  }
  const sameFrameworkCode = (a, b) =>
    String(a?.frameworkCode ?? a?.code ?? a?.framework ?? '').toUpperCase() ===
    String(b?.frameworkCode ?? b?.code ?? b?.framework ?? '').toUpperCase()
  const matchingSummaryFrameworkStatus = (row) =>
    frameworkStatusRows(selectedAssessmentSummary).find((item) => sameFrameworkCode(item, row)) ?? null
  const assessmentFrameworksLabel = (item) => {
    const rows = frameworkStatusRows(item)
    if (rows.length > 0) {
      return rows
        .map((row) => row.frameworkCode ?? row.code ?? row.framework ?? 'Framework')
        .filter(Boolean)
        .join(', ')
    }
    const frameworks = item?.frameworks ?? item?.frameworkTags ?? []
    return Array.isArray(frameworks) && frameworks.length > 0 ? frameworks.join(', ') : '—'
  }
  const assessmentConsultantLabel = (item) => {
    const staffLists = [
      item?.assignedStaff,
      item?.projectConsultants,
      item?.consultants,
      item?.project?.assignedStaff,
      item?.project?.projectConsultants,
      item?.project?.consultants,
    ]
    for (const list of staffLists) {
      if (!Array.isArray(list) || list.length === 0) continue
      const names = list
        .map((staff) => {
          if (typeof staff === 'string') return staff.trim()
          if (!staff || typeof staff !== 'object') return ''
          const fromParts = `${staff.firstName ?? ''} ${staff.lastName ?? ''}`.trim()
          return fromParts || String(staff.fullName ?? staff.email ?? '').trim()
        })
        .filter(Boolean)
      if (names.length > 0) return names.join(', ')
    }

    const nameLists = [
      item?.assignedStaffNames,
      item?.projectConsultantNames,
      item?.project?.assignedStaffNames,
      item?.project?.projectConsultantNames,
    ]
    for (const list of nameLists) {
      if (!Array.isArray(list) || list.length === 0) continue
      const names = list.map((name) => String(name ?? '').trim()).filter(Boolean)
      if (names.length > 0) return names.join(', ')
    }

    const fallback =
      item?.consultantName ??
      item?.assignedConsultantName ??
      item?.assignedConsultantEmail ??
      item?.consultant?.fullName ??
      item?.consultant?.email ??
      item?.project?.consultantName ??
      item?.project?.assignedConsultantName ??
      item?.client?.assignedConsultantName ??
      item?.client?.assignedConsultantEmail ??
      item?.client?.consultantName ??
      item?.client?.consultantEmail ??
      null
    if (fallback && typeof fallback === 'object') {
      const fromParts = `${fallback.firstName ?? ''} ${fallback.lastName ?? ''}`.trim()
      return fromParts || fallback.fullName || fallback.email || '—'
    }
    return fallback || '—'
  }
  const assessmentSubmittedDateValue = (item) =>
    latestDateValue(
      item?.submittedAt,
      item?.submitted_at,
      item?.lastSubmittedAt,
      item?.lastSubmissionDate,
      item?.updatedAt,
      item?.updated_at,
      item?.createdAt,
      item?.created_at,
    )
  const globalAssessmentRows = allAssessments.filter((item) => {
    const expectedStatus = staffSubView === 'assessment-submitted' ? 'Submitted' : 'Current Assessment'
    if (assessmentStatusLabel(item) !== expectedStatus) return false

    const clientFilter = assessmentFilters.client
    if (clientFilter && String(item?.client?.id ?? item?.clientId ?? '') !== clientFilter) return false

    return true
  })
  const assessmentClientOptions = clients.filter((client) =>
    allAssessments.some((item) => {
      const expectedStatus = staffSubView === 'assessment-submitted' ? 'Submitted' : 'Current Assessment'
      const assessmentClientId = item?.client?.id ?? item?.clientId
      return assessmentStatusLabel(item) === expectedStatus && String(assessmentClientId ?? '') === String(client.id)
    }),
  )
  const assessmentClientSearchTerm = assessmentClientSearch.trim().toLowerCase()
  const searchableAssessmentClientOptions = assessmentClientOptions.filter((client) => {
    if (!assessmentClientSearchTerm) return true
    const name = String(client.fullName ?? client.name ?? client.email ?? '').toLowerCase()
    return name.includes(assessmentClientSearchTerm)
  })
  const selectedAssessmentClient = assessmentClientOptions.find((client) => String(client.id) === assessmentFilters.client)
  function selectAssessmentClientFilter(clientId = '') {
    setAssessmentFilters({ client: clientId ? String(clientId) : '' })
    setAssessmentClientSearch('')
    setAssessmentClientMenuOpen(false)
  }
  function onAssessmentClientSearchKeyDown(e) {
    if (e.key === 'Escape') {
      e.preventDefault()
      setAssessmentClientSearch('')
      setAssessmentClientMenuOpen(false)
      return
    }
    if (e.key !== 'Enter') return
    e.preventDefault()
    const firstMatch = searchableAssessmentClientOptions[0]
    if (firstMatch) {
      selectAssessmentClientFilter(firstMatch.id)
    } else if (!assessmentClientSearchTerm) {
      selectAssessmentClientFilter('')
    }
  }
  const showAssessmentProjectList = staffTab === 'projects' && isAssessmentProjectView(staffSubView)
  const assessmentsViewportActive = showAssessmentProjectList && assessmentStep === 'global'

  useEffect(() => {
    if (!showAssessmentProjectList || !assessmentFilters.client) return
    const selectedClientStillVisible = assessmentClientOptions.some((client) => String(client.id) === assessmentFilters.client)
    if (!selectedClientStillVisible) {
      setAssessmentFilters({ client: '' })
      setAssessmentClientMenuOpen(false)
      setAssessmentClientSearch('')
    }
  }, [assessmentClientOptions, assessmentFilters.client, showAssessmentProjectList])
  const canExportAssessmentPdf =
    isStaff &&
    isSubmittedAssessment({
      status: assessment?.status,
    })

  const canShowRecommendationActions =
    canUseAiRecommendations &&
    isSubmittedAssessment({
      status: assessment?.status,
    })

  function resolveAssessmentOpenId(row) {
    if (!row) return null
    if (staffSubView === 'assessment-submitted') {
      return row.latestSubmittedAssessmentId ?? row.id ?? row.assessmentId ?? null
    }
    return row.id ?? row.assessmentId ?? null
  }

  function onRecommendationTargetSaved(response) {
    setAssessment((prev) =>
      prev
        ? {
            ...prev,
            recommendationTargetScore:
              response?.recommendationTargetScore ?? response?.targetScore ?? prev.recommendationTargetScore,
          }
        : prev,
    )
  }

  function onExportAssessmentPdf() {
    if (!isStaff || !assessment) return
    exportAssessmentPdf(
      buildAdminAssessmentPdfReport({
        clientName: detailDisplayClient?.fullName ?? detailDisplayClient?.email ?? `Client ${selectedClientId ?? ''}`,
        assessment,
      }),
    )
  }

  function openAssessmentClient(clientId) {
    if (!canOpenAssessmentVersions) {
      selectStaffTab('projects', 'assessment-submitted')
      return
    }
    const client = clients.find((item) => item.id === clientId) ?? null
    setSelectedClientId(clientId)
    setSelectedAssessmentId(null)
    setAssessment(null)
    setDetailClient(client)
    setAssessmentStep('versions')
  }

  function openAssessmentDetails(assessmentId, client = null) {
    setSelectedAssessmentId(assessmentId)
    setAssessment(null)
    setDetailClient(client ?? selectedClient)
    setAssessmentDetailBackStep(staffSubView === 'assessment-submitted' || staffSubView === 'assessment-draft' ? 'global' : 'versions')
    setAssessmentStep('details')
  }

  async function openLatestProjectAssessment(client, edit = false) {
    const clientId = client?.id ?? client?.clientId
    if (!clientId) return
    setError('')
    try {
      const rows = await apiFetch(`/api/admin/clients/${clientId}/assessments`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      const assessmentRow = Array.isArray(rows) ? rows[0] : null
      const assessmentId =
        assessmentRow?.latestSubmittedAssessmentId ?? assessmentRow?.id ?? assessmentRow?.assessmentId
      if (!assessmentId) {
        setError('No assessment found for this project.')
        return
      }
      if (edit) {
        navigate(staffAssessmentEditPathForRole(role, assessmentId))
        return
      }
      setStaffTab('projects')
      setOpenStaffMenu(isConsultant ? '' : 'projects')
      setStaffSubView('assessment-submitted')
      setAssessmentDetailBackStep('project-existing')
      setSelectedAssessmentId(assessmentId)
      setAssessment(null)
      setDetailClient(client)
      setAssessmentStep('details')
    } catch (err) {
      setError(err?.message ?? 'Could not open project assessment')
    }
  }

  function backFromAssessmentDetails() {
    if (assessmentDetailBackStep === 'project-existing') {
      setStaffTab('projects')
      setOpenStaffMenu(isConsultant ? '' : 'projects')
      setStaffSubView('project-existing')
      setAssessmentStep('clients')
      setSelectedAssessmentId(null)
      setAssessment(null)
      return
    }
    setAssessmentStep(assessmentDetailBackStep)
  }

  async function openAssessmentVersionDetails(versionId) {
    if (!canOpenAssessmentVersions) {
      selectStaffTab('projects', 'assessment-submitted')
      return
    }
    if (!selectedClientId || !versionId) return
    setSelectedAssessmentId(null)
    setAssessment(null)
    setDetailClient(selectedClient)
    setAssessmentDetailBackStep('versions')
    setAssessmentStep('details')
    try {
      const raw = await apiFetch(assessmentVersionDetailPath(selectedClientId, versionId), {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      setAssessment(normalizeVersionDetail(raw))
    } catch (err) {
      setError(err?.message ?? 'Could not load version details')
    }
  }

  function openAssessmentVersionsForRow(row, client) {
    if (!canOpenAssessmentVersions) return
    const clientId = client?.id ?? row?.client?.id ?? row?.clientId
    if (!clientId) return
    setVersionOverlayClient({
      id: clientId,
      label: client?.fullName ?? row?.clientName ?? client?.email ?? row?.clientEmail ?? `Client ${clientId}`,
    })
  }

  function selectStaffTab(tab, subView = null) {
    if (isConsultant) {
      setStaffTab('projects')
      setOpenStaffMenu('')
      setStaffSubView('project-existing')
      setSelectedAssessmentId(null)
      setAssessment(null)
      setAssessmentStep('clients')
      setSidebarOpen(false)
      return
    }
    setStaffTab(tab)
    setOpenStaffMenu((current) => (current === tab && subView == null ? '' : tab))
    if (subView) setStaffSubView(subView)
    if (tab === 'dashboard') setStaffSubView('overview')
    if (tab === 'projects' && isAssessmentProjectView(subView)) {
      setProjectAssessmentsOpen(true)
      setError('')
      setStaffSubView(subView)
      setSelectedAssessmentId(null)
      setAssessment(null)
      setAssessmentStep('global')
    }
    if (tab === 'projects' && (subView === 'project-list' || subView === 'project-add-consultant')) {
      setProjectAssessmentsOpen(true)
    }
    if (tab === 'projects' && (subView === 'project-create' || subView === 'team-assign-consultant')) {
      setProjectNewOpen(true)
    }
    if (tab === 'team' && !subView) setStaffSubView('team-add-client')
    if (tab === 'projects' && !subView) setStaffSubView('project-create')
    if (tab === 'frameworks' && !subView) setStaffSubView('framework-create')
    if (subView || tab === 'dashboard') setSidebarOpen(false)
  }

  function toggleExistingProjectsMenu() {
    setStaffTab('projects')
    setOpenStaffMenu('projects')
    setStaffSubView('project-existing')
    setProjectAssessmentsOpen((open) => !open)
    setSelectedAssessmentId(null)
    setAssessment(null)
  }

  function toggleNewProjectMenu() {
    setStaffTab('projects')
    setOpenStaffMenu('projects')
    setProjectNewOpen(true)
    setStaffSubView((current) =>
      current === 'project-create' || current === 'team-assign-consultant' ? current : 'project-create',
    )
    setSelectedAssessmentId(null)
    setAssessment(null)
  }

  const detailFrameworkStatus = frameworkStatusRows(assessment).length
    ? frameworkStatusRows(assessment)
    : frameworkStatusRows(selectedAssessmentSummary)
  const sharedFrameworkProps = {
    sharedFrameworkCatalog: frameworkCatalog,
    sharedFrameworkCatalogLoading: frameworkCatalogLoading,
    sharedFrameworkCatalogError: frameworkCatalogError,
    onRetryFrameworkCatalog: () => setFrameworkCatalogTick((n) => n + 1),
  }
  return (
    <div className="container">
      <div className={assessmentsViewportActive ? 'page pageAssessmentsViewport' : 'page'}>
        {error ? <div className="alert alertError">{error}</div> : null}
        {success ? <div className="alert alertSuccess">{success}</div> : null}
        {loading ? <p>Loading…</p> : null}

        {!loading ? (
          <div className={assessmentsViewportActive ? 'staffWorkspace staffWorkspaceAssessments' : 'staffWorkspace'}>
            {sidebarOpen ? (
              <button
                type="button"
                className="staffSidebarBackdrop"
                aria-label="Close staff menu"
                onClick={() => setSidebarOpen(false)}
              />
            ) : null}
            <aside className={sidebarOpen ? 'staffSidebar staffSidebarOpen' : 'staffSidebar'} aria-label="Staff navigation">
              <div className="staffSidebarBrand">
                <div className="staffSidebarIcon">
                  <BriefcaseBusiness size={20} strokeWidth={2.2} />
                </div>
                <div className="staffSidebarBrandText">
                  <strong>Data Maturity Assessment</strong>
                  <span>{role || 'STAFF'}</span>
                </div>
                <button type="button" className="staffSidebarClose" aria-label="Close menu" onClick={() => setSidebarOpen(false)}>
                  <X size={18} />
                </button>
              </div>
              <button
                type="button"
                className={
                  (isConsultant ? staffTab === 'projects' && staffSubView === 'project-existing' : staffTab === 'dashboard')
                    ? 'staffNavItem staffNavItemActive'
                    : 'staffNavItem'
                }
                onClick={() => selectStaffTab(isConsultant ? 'projects' : 'dashboard', isConsultant ? 'project-existing' : null)}
              >
                {isConsultant ? <FolderKanban size={18} /> : <BarChart3 size={18} />}
                {isConsultant ? 'Existing Projects' : 'Dashboard'}
              </button>
              {showTeamTab ? (
                <div className="staffNavGroup">
                  <button
                    type="button"
                    className={staffTab === 'projects' ? 'staffNavItem staffNavItemActive' : 'staffNavItem'}
                    onClick={() => selectStaffTab('projects')}
                    aria-expanded={openStaffMenu === 'projects'}
                  >
                    <FolderKanban size={18} />
                    <span className="staffNavText">Projects</span>
                    <ChevronDown className="staffNavChevron" size={16} />
                  </button>
                  {openStaffMenu === 'projects' ? (
                    <div className="staffSubNav">
                      <div className="staffSubNavBranch">
                        <div className="staffSubNavBranchRow">
                          <button
                            type="button"
                            className={staffSubView === 'project-existing' ? 'staffSubNavItem staffSubNavItemActive' : 'staffSubNavItem'}
                            aria-expanded={projectAssessmentsOpen}
                            onClick={toggleExistingProjectsMenu}
                          >
                            Existing projects
                          </button>
                          <button
                            type="button"
                            className="staffSubNavToggle"
                            aria-label={projectAssessmentsOpen ? 'Hide assessment project lists' : 'Show assessment project lists'}
                            aria-expanded={projectAssessmentsOpen}
                            onClick={toggleExistingProjectsMenu}
                          >
                            <ChevronDown size={14} />
                          </button>
                        </div>
                        {projectAssessmentsOpen ? (
                          <div className="staffSubNavNested">
                            {[
                              ['assessment-draft', 'Current Assessments'],
                              ['assessment-submitted', 'Submitted assessments'],
                              ['project-add-consultant', 'Add Consultant To Project'],
                              ['project-list', 'Add Framework To Project'],
                            ].map(([key, label]) => (
                              <button
                                key={key}
                                type="button"
                                className={staffSubView === key ? 'staffSubNavItem staffSubNavItemActive' : 'staffSubNavItem'}
                                onClick={() => selectStaffTab('projects', key)}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        ) : null}
                      </div>
                      <div className="staffSubNavBranch">
                        <div className="staffSubNavBranchRow">
                          <button
                            type="button"
                            className={
                              staffSubView === 'project-create' ||
                              staffSubView === 'team-assign-consultant' ||
                              staffSubView === 'project-new'
                                ? 'staffSubNavItem staffSubNavItemActive'
                                : 'staffSubNavItem'
                            }
                            aria-expanded={projectNewOpen}
                            onClick={toggleNewProjectMenu}
                          >
                            New Project
                          </button>
                          <button
                            type="button"
                            className="staffSubNavToggle"
                            aria-label={projectNewOpen ? 'Hide new project menu' : 'Show new project menu'}
                            aria-expanded={projectNewOpen}
                            onClick={() => setProjectNewOpen((open) => !open)}
                          >
                            <ChevronDown size={14} />
                          </button>
                        </div>
                        {projectNewOpen ? (
                          <div className="staffSubNavNested">
                            {[
                              ['project-create', 'Create New Project'],
                              ['team-assign-consultant', 'Assign Consultant To Project'],
                            ].map(([key, label]) => (
                              <button
                                key={key}
                                type="button"
                                className={staffSubView === key ? 'staffSubNavItem staffSubNavItemActive' : 'staffSubNavItem'}
                                onClick={() => selectStaffTab('projects', key)}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {showTeamTab ? (
                <div className="staffNavGroup">
                  <button
                    type="button"
                    className={staffTab === 'team' ? 'staffNavItem staffNavItemActive' : 'staffNavItem'}
                    onClick={() => selectStaffTab('team')}
                    aria-expanded={openStaffMenu === 'team'}
                  >
                    <Users size={18} />
                    <span className="staffNavText">Users</span>
                    <ChevronDown className="staffNavChevron" size={16} />
                  </button>
                  {openStaffMenu === 'team' ? (
                    <div className="staffSubNav">
                      {[
                        ['team-add-client', 'Add client'],
                        ['team-add-consultant', 'Add consultant'],
                        ['team-staff-list', 'Consultants & Managers List'],
                      ].map(([key, label]) => (
                        <button
                          key={key}
                          type="button"
                          className={staffSubView === key ? 'staffSubNavItem staffSubNavItemActive' : 'staffSubNavItem'}
                          onClick={() => selectStaffTab('team', key)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
              {isAdmin ? (
                <div className="staffNavGroup">
                  <button
                    type="button"
                    className={staffTab === 'frameworks' ? 'staffNavItem staffNavItemActive' : 'staffNavItem'}
                    onClick={() => selectStaffTab('frameworks')}
                    aria-expanded={openStaffMenu === 'frameworks'}
                  >
                    <Layers3 size={18} />
                    <span className="staffNavText">Frameworks</span>
                    <ChevronDown className="staffNavChevron" size={16} />
                  </button>
                  {openStaffMenu === 'frameworks' ? (
                    <div className="staffSubNav">
                      {[
                        ['framework-create', 'Create framework'],
                      ].map(([key, label]) => (
                        <button
                          key={key}
                          type="button"
                          className={staffSubView === key ? 'staffSubNavItem staffSubNavItemActive' : 'staffSubNavItem'}
                          onClick={() => selectStaffTab('frameworks', key)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </aside>
            <main className="staffMainPanel">
              <button
                type="button"
                className="staffMenuButton"
                aria-label="Open staff menu"
                onClick={() => setSidebarOpen(true)}
              >
                <Menu size={20} />
              </button>
        {staffTab === 'dashboard' && (isAdmin || isManager) ? (
          <ManagerDashboardView
            loading={dashboardLoading}
            role={role}
            stats={dashboardStats}
            clientCount={clients.length}
            assessments={allAssessments}
            consultants={dashboardConsultants}
            managers={dashboardManagers}
            projects={dashboardProjects}
            frameworks={frameworkCatalog}
          />
        ) : null}

        {staffTab === 'frameworks' && isAdmin ? (
          <section className="staffDashboardView">
            {staffSubView === 'framework-list' ? (
              <FrameworkCatalogPanel
                frameworks={frameworkCatalog}
                loading={frameworkCatalogLoading}
                error={frameworkCatalogError}
                onRetry={() => setFrameworkCatalogTick((n) => n + 1)}
              />
            ) : (
              <AddFrameworkPanel token={auth.token} />
            )}
          </section>
        ) : null}

        {staffTab === 'team' && showTeamTab ? (
          <StaffTeamPanel
            token={auth.token}
            role={role}
            clients={clients}
            onClientsRefresh={refreshClientsAndSelection}
            view={staffSubView}
          {...sharedFrameworkProps}
          />
        ) : null}

        {staffTab === 'projects' && staffSubView === 'project-existing' && (showTeamTab || isConsultant) ? (
          <StaffTeamPanel
            token={auth.token}
            role={role}
            clients={clients}
            onClientsRefresh={refreshClientsAndSelection}
            view="project-existing"
            readOnly
            onViewProjectDetails={isConsultant ? (client) => openLatestProjectAssessment(client, false) : undefined}
            onEditProjectAssessment={isConsultant ? (client) => openLatestProjectAssessment(client, true) : undefined}
          {...sharedFrameworkProps}
          />
        ) : null}

        {staffTab === 'projects' &&
        showTeamTab &&
        !showAssessmentProjectList &&
        staffSubView !== 'project-existing' &&
        staffSubView !== 'project-new' ? (
          <StaffTeamPanel
            token={auth.token}
            role={role}
            clients={clients}
            onClientsRefresh={refreshClientsAndSelection}
            view={staffSubView}
          {...sharedFrameworkProps}
          />
        ) : null}

        {showAssessmentProjectList ? (
          <section className="assessmentFlow">
            {assessmentStep === 'clients' ? (
              <>
                <div className="staffViewHeader">
                  <div>
                    <h2 className="sectionTitle">Assessments</h2>
                    <p className="sectionHint">Select a client to open their assessment versions.</p>
                  </div>
                  <div className="badge">{clients.length} clients</div>
                </div>
                <div className="assessmentCardGrid">
                  {clients.map((c) => (
                    <article key={c.id} className="assessmentFlowCard">
                      <div>
                        <div className="listTitle">{c.fullName ?? c.email}</div>
                        <div className="listSub">{c.email}</div>
                      </div>
                      <div className="assessmentCardActions">
                        <button type="button" className="btn btnPrimary btnSm" onClick={() => openAssessmentClient(c.id)}>
                          View versions
                        </button>
                      </div>
                    </article>
                  ))}
                  {clients.length === 0 ? <div className="sectionCard muted">No clients.</div> : null}
                </div>
              </>
            ) : null}

            {assessmentStep === 'versions' ? (
              <>
                <div className="staffViewHeader">
                  <div>
                    <button type="button" className="btn btnGhost btnSm" onClick={() => setAssessmentStep('clients')}>
                      Back to clients
                    </button>
                    <h2 className="sectionTitle" style={{ marginTop: 12 }}>
                      {selectedClient?.fullName ?? selectedClient?.email ?? 'Client versions'}
                    </h2>
                    <p className="sectionHint">Assessment versions for this client. Open a version to view details.</p>
                  </div>
                  <div className="badge">{assessmentVersions.length} versions</div>
                </div>
                {assessmentVersionsError ? <div className="alert alertError">{assessmentVersionsError}</div> : null}
                {assessmentVersionsLoading ? <p className="muted">Loading versions...</p> : null}
                <div className="tableWrap">
                  <table className="dataTable">
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Created</th>
                        <th>Framework</th>
                        <th>Overall Score</th>
                        <th>Overall Average Score</th>
                        <th>Status</th>
                        <th aria-label="Actions" />
                      </tr>
                    </thead>
                    <tbody>
                      {assessmentVersions.map((version) => (
                        <tr key={String(version.id)}>
                          <td>
                            Version {version.versionNumber}
                            {version.versionComment ? ` — ${version.versionComment}` : ''}
                            {version.isLatest ? <span className="badge" style={{ marginLeft: 8 }}>Latest</span> : null}
                          </td>
                          <td>{formatSubmittedDate(version.createdAt) || '—'}</td>
                          <td>{version.framework}</td>
                          <td>{version.globalScore ?? '—'}</td>
                          <td>{version.globalAverageScore ?? '—'}</td>
                          <td>{assessmentStatusLabel(version)}</td>
                          <td className="cellActions">
                            <button
                              type="button"
                              className="btn btnPrimary btnSm"
                              onClick={() => openAssessmentVersionDetails(version.id)}
                            >
                              Details
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!assessmentVersionsLoading && assessmentVersions.length === 0 ? (
                    <div className="muted">No assessment versions returned for this client.</div>
                  ) : null}
                </div>
              </>
            ) : null}

            {assessmentStep === 'global' ? (
              <section className="sectionCard assessmentListCard">
                <div className="sectionHeader">
                  <SectionHeading
                    icon={staffSubView === 'assessment-submitted' ? ClipboardCheck : ClipboardList}
                    title={staffSubView === 'assessment-submitted' ? 'Submitted Assessments' : 'Current Assessments'}
                    subtitle={`All ${staffSubView === 'assessment-submitted' ? 'submitted' : 'current'} assessments across every client.`}
                    badge={globalAssessmentRows.length}
                  />
                </div>

                <div className="assessmentFilters">
                  <label className="field">
                    <span className="label">Client</span>
                    <div className="clientFilterDropdown">
                      <button
                        type="button"
                        className="clientFilterButton"
                        onClick={() => {
                          setAssessmentClientSearch('')
                          setAssessmentClientMenuOpen((open) => !open)
                        }}
                        aria-expanded={assessmentClientMenuOpen}
                        aria-haspopup="listbox"
                      >
                        <span>
                          {selectedAssessmentClient?.fullName ?? selectedAssessmentClient?.email ?? 'All clients'}
                        </span>
                        <ChevronDown size={16} />
                      </button>
                      {assessmentClientMenuOpen ? (
                        <div className="clientFilterMenu" role="listbox">
                          <button
                            type="button"
                            className={assessmentFilters.client === '' ? 'clientFilterOption clientFilterOptionActive' : 'clientFilterOption'}
                            onClick={() => selectAssessmentClientFilter('')}
                          >
                            All clients
                          </button>
                          <div className="clientFilterSearchWrap">
                            <input
                              type="search"
                              className="clientFilterSearchInput"
                              value={assessmentClientSearch}
                              placeholder="Search client by name..."
                              autoFocus
                              onChange={(e) => setAssessmentClientSearch(e.target.value)}
                              onKeyDown={onAssessmentClientSearchKeyDown}
                            />
                          </div>
                          <div className="clientFilterScroll">
                            {searchableAssessmentClientOptions.map((client) => (
                              <button
                                key={client.id}
                                type="button"
                                className={
                                  String(client.id) === assessmentFilters.client
                                    ? 'clientFilterOption clientFilterOptionActive'
                                    : 'clientFilterOption'
                                }
                                onClick={() => selectAssessmentClientFilter(client.id)}
                              >
                                {client.fullName ?? client.email}
                              </button>
                            ))}
                            {searchableAssessmentClientOptions.length === 0 ? (
                              <div className="clientFilterEmpty">
                                {assessmentClientOptions.length === 0 ? 'No clients for this status.' : 'No clients match your search.'}
                              </div>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className="clientFilterBackdrop"
                      aria-label="Close client filter"
                      hidden={!assessmentClientMenuOpen}
                      onClick={() => {
                        setAssessmentClientSearch('')
                        setAssessmentClientMenuOpen(false)
                      }}
                      tabIndex={-1}
                    />
                    <input
                      type="hidden"
                      value={assessmentFilters.client}
                      readOnly
                    />
                  </label>
                </div>

                <div className="tableWrap proTableWrap proTableDesktopOnly">
                  <table className="dataTable proTable assessmentListTable">
                    <thead>
                      <tr>
                        <th>Client</th>
                        <th>Framework</th>
                        <th>Version</th>
                        <th>Submission date</th>
                        <th>Assigned Consultant</th>
                        <th>Status</th>
                        <th aria-label="Actions" />
                      </tr>
                    </thead>
                    <tbody>
                      {globalAssessmentRows.map((row) => {
                        const client = row.client ?? clients.find((item) => item.id === row.clientId) ?? null
                        const version = row.currentVersion ?? row.version ?? row.versionNumber ?? '—'
                        const statusLabel = assessmentStatusLabel(row)
                        const statusClass =
                          assessmentStatusValue(row) === 'SUBMITTED'
                            ? 'proBadge proBadgeSubmitted proBadgeWithIcon'
                            : assessmentStatusValue(row) === 'DRAFT' || assessmentStatusValue(row) === 'IN_PROGRESS'
                              ? 'proBadge proBadgeCurrent proBadgeWithIcon'
                              : 'proBadge proBadgeNeutral'
                        const StatusIcon =
                          assessmentStatusValue(row) === 'SUBMITTED'
                            ? CircleCheck
                            : assessmentStatusValue(row) === 'DRAFT' || assessmentStatusValue(row) === 'IN_PROGRESS'
                              ? ClipboardList
                              : null
                        return (
                          <tr key={`${row.id}-${client?.id ?? 'client'}`}>
                            <td className="assessmentClientCell">
                              <strong>{client?.fullName ?? row.clientName ?? client?.email ?? '—'}</strong>
                              <div className="tinyNote">{client?.email ?? row.clientEmail ?? ''}</div>
                            </td>
                            <td className="assessmentFwCell">{assessmentFrameworksLabel(row)}</td>
                            <td>{`Version ${version}`}</td>
                            <td>{formatSubmittedDate(assessmentSubmittedDateValue(row)) || '—'}</td>
                            <td>{assessmentConsultantLabel(row)}</td>
                            <td className="assessmentStatusCell">
                              <span className={statusClass}>
                                {StatusIcon ? <StatusIcon size={12} strokeWidth={2.4} aria-hidden="true" /> : null}
                                {statusLabel}
                              </span>
                            </td>
                            <td className="cellActions">
                              <div className="cellActionsInner">
                                {canOpenAssessmentVersions ? (
                                  <button
                                    type="button"
                                    className="btn btnGhost btnSm btnWithIcon"
                                    onClick={() => openAssessmentVersionsForRow(row, client)}
                                  >
                                    <BtnIcon icon={History} />
                                    Assessment Versions
                                  </button>
                                ) : null}
                                <button
                                  type="button"
                                  className="btn btnPrimary btnSm btnWithIcon"
                                  onClick={() => openAssessmentDetails(resolveAssessmentOpenId(row), client)}
                                >
                                  <BtnIcon icon={Eye} />
                                  View Details
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  {globalAssessmentRows.length === 0 ? (
                    <div className="proEmptyState">No assessments match these filters.</div>
                  ) : null}
                </div>

                <div className="proMobileList">
                  {globalAssessmentRows.length === 0 ? (
                    <div className="proEmptyState">No assessments match these filters.</div>
                  ) : (
                    globalAssessmentRows.map((row) => {
                      const client = row.client ?? clients.find((item) => item.id === row.clientId) ?? null
                      const version = row.currentVersion ?? row.version ?? row.versionNumber ?? '—'
                      const statusLabel = assessmentStatusLabel(row)
                      const statusClass =
                        assessmentStatusValue(row) === 'SUBMITTED'
                          ? 'proBadge proBadgeSubmitted proBadgeWithIcon'
                          : assessmentStatusValue(row) === 'DRAFT' || assessmentStatusValue(row) === 'IN_PROGRESS'
                            ? 'proBadge proBadgeCurrent proBadgeWithIcon'
                            : 'proBadge proBadgeNeutral'
                      const StatusIcon =
                        assessmentStatusValue(row) === 'SUBMITTED'
                          ? CircleCheck
                          : assessmentStatusValue(row) === 'DRAFT' || assessmentStatusValue(row) === 'IN_PROGRESS'
                            ? ClipboardList
                            : null
                      return (
                        <article key={`m-${row.id}-${client?.id ?? 'client'}`} className="proMobileCard">
                          <div>
                            <strong>{client?.fullName ?? row.clientName ?? client?.email ?? '—'}</strong>
                            <div className="tinyNote">{client?.email ?? row.clientEmail ?? ''}</div>
                          </div>
                          <div>
                            <span className="proMobileLabel">Framework</span>
                            {assessmentFrameworksLabel(row)}
                          </div>
                          <div>
                            <span className="proMobileLabel">Version</span>
                            Version {version}
                          </div>
                          <div>
                            <span className="proMobileLabel">Status</span>
                            <span className={statusClass}>
                              {StatusIcon ? <StatusIcon size={12} strokeWidth={2.4} aria-hidden="true" /> : null}
                              {statusLabel}
                            </span>
                          </div>
                          <div className="cellActions">
                            {canOpenAssessmentVersions ? (
                              <button
                                type="button"
                                className="btn btnGhost btnSm btnWithIcon"
                                onClick={() => openAssessmentVersionsForRow(row, client)}
                              >
                                <BtnIcon icon={History} />
                                Assessment Versions
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="btn btnPrimary btnSm btnWithIcon"
                              onClick={() => openAssessmentDetails(resolveAssessmentOpenId(row), client)}
                            >
                              <BtnIcon icon={Eye} />
                              View Details
                            </button>
                          </div>
                        </article>
                      )
                    })
                  )}
                </div>
              </section>
            ) : null}

            {assessmentStep === 'details' ? (
              <section className="sectionCard adminDetails">
                <div className="sectionHeader">
                  <div>
                    <button type="button" className="btn btnGhost btnSm btnWithIcon" onClick={backFromAssessmentDetails}>
                      <BtnIcon icon={ArrowLeft} />
                      {assessmentDetailBackStep === 'versions'
                        ? 'Back to versions'
                        : assessmentDetailBackStep === 'project-existing'
                          ? 'Back to projects'
                          : 'Back to list'}
                    </button>
                    <div style={{ marginTop: 12 }}>
                      <SectionHeading
                        icon={ClipboardList}
                        title="Assessment Details"
                        subtitle={
                          detailDisplayClient
                            ? detailDisplayClient.fullName ?? detailDisplayClient.email
                            : undefined
                        }
                      />
                    </div>
                    {assessment ? (
                      <div className="sectionHint">
                        <div>
                          Overall Score: <strong>{frameworkAvg ?? assessment.globalScore ?? assessment.score ?? '—'}</strong> / 5
                          {frameworkMaturityLabel ? <> — {maturityLabelEn(frameworkMaturityLabel)}</> : null}
                        </div>
                        <div>
                          Overall Average Score: <strong>{frameworkAverageScore ?? '—'}</strong> / 5
                        </div>
                        {frameworkAverages.length > 0 ? (
                          <div style={{ display: 'grid', gap: 4, marginTop: 8 }}>
                            {frameworkAverages.map((item) => (
                              <div key={item.key}>
                                Overall Score {item.label}: <strong>{item.avg ?? '—'}</strong> / 5 · Overall Average Score:{' '}
                                <strong>{item.averageScore ?? '—'}</strong> / 5
                              </div>
                            ))}
                          </div>
                        ) : null}
                        {detailFrameworkStatus.length > 0 ? (
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                            {detailFrameworkStatus.map((item) => {
                              const statusLabel = frameworkStatusLabel(item)
                              const summaryStatus = matchingSummaryFrameworkStatus(item)
                              const frameworkCode = item.frameworkCode ?? item.code ?? item.framework
                              const submittedDate =
                                isFrameworkSubmitted(item)
                                  ? formatSubmittedDate(
                                      latestDateValue(
                                        frameworkSubmittedDate(item),
                                        frameworkSubmittedDate(summaryStatus),
                                        latestAnswerDateForFramework(frameworkCode),
                                      ),
                                    )
                                  : ''
                              return (
                                <span key={item.frameworkCode} className="badge">
                                  {item.frameworkCode}: {statusLabel}
                                  {item.totalQuestions ? ` (${item.answeredQuestions}/${item.totalQuestions})` : ''}
                                  {submittedDate ? <span className="badgeSubtleText">submitted: {submittedDate}</span> : null}
                                </span>
                              )
                            })}
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <p className="sectionHint">Loading assessment details...</p>
                    )}
                    {assessment && canShowRecommendationActions ? (
                      <RecommendationActionsPanel
                        assessment={assessment}
                        token={auth.token}
                        canUseRecommendations={canShowRecommendationActions}
                        onTargetSaved={onRecommendationTargetSaved}
                        onError={(message) => {
                          setSuccess('')
                          setError(message || '')
                        }}
                        onSuccess={(message) => {
                          setError('')
                          setSuccess(message || '')
                        }}
                      />
                    ) : null}
                  </div>
                  {assessment ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      {canExportAssessmentPdf ? (
                        <button type="button" className="btn btnGhost btnSm btnWithIcon" onClick={onExportAssessmentPdf}>
                          <BtnIcon icon={FileDown} />
                          Export Assessment Report
                        </button>
                      ) : null}
                      <div className="badge">{assessmentStatusLabel(assessment)}</div>
                      {isStaff ? (
                        <button
                          type="button"
                          className="btn btnPrimary btnSm btnWithIcon"
                          onClick={() => navigate(staffAssessmentEditPathForRole(role, assessment.id ?? selectedAssessmentId))}
                        >
                          <BtnIcon icon={Pencil} />
                          Edit
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>

                {assessment ? (
                  <AssessmentDetailsDomains
                    segments={assessmentDomains}
                    recommendations={assessment.recommendations}
                    assessmentId={assessment.id ?? selectedAssessmentId}
                    token={auth.token}
                    interactive
                    onUploadEvidence={uploadEvidenceForAnswer}
                    onRateEvidence={rateEvidence}
                    canUseAcceptanceCriteria={canUseAiRecommendations}
                    onAcceptanceCriteriaReport={generateAcceptanceCriteriaReport}
                    canDeleteEvidence={canUseAiRecommendations}
                    onDeleteEvidence={removeEvidence}
                    onError={setError}
                    onSuccess={setSuccess}
                  />
                ) : null}
              </section>
            ) : null}
          </section>
        ) : null}
            </main>
          </div>
        ) : null}

        {versionOverlayClient && canOpenAssessmentVersions ? (
          <AssessmentVersioningOverlay
            clientId={versionOverlayClient.id}
            clientLabel={versionOverlayClient.label}
            token={auth.token}
            onClose={() => setVersionOverlayClient(null)}
          />
        ) : null}

      </div>
    </div>
  )
}

