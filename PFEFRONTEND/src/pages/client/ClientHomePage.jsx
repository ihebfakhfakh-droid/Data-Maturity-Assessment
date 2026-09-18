import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, CircleCheck, Clock, FileText, Upload } from 'lucide-react'
import { apiFetch, apiFetchFormData } from '../../api/client.js'
import { useAuth } from '../../auth/AuthProvider.jsx'
import { homePathForRole, isStaffRole, normalizeRole, roleFromAuth } from '../../auth/roles.js'
import { deleteEvidence } from '../../api/evidenceApi.js'
import { EvidenceDeleteConfirmModal, EvidenceFilesPanel } from '../../components/EvidenceFilesPanel.jsx'
import { BtnIcon } from '../../ui/IconBox.jsx'
import { exportAssessmentPdf, isSubmittedAssessment } from '../../utils/assessmentPdf.js'
import { markLatestVersion, normalizeVersionRow } from '../admin/assessmentVersioningApi.js'
import { FrameworkRadarChart } from './FrameworkRadarChart.jsx'
import { SegmentRadarChart } from './SegmentRadarChart.jsx'
// Statistics: spider charts only (domains + questions)

const EMPTY_ASSESSMENT_VERSIONS_MESSAGE = 'You do not have any assessment versions yet.'

/** Parent domain names for CMMI DMM (key = first number in codes like cmmi_2_1). */
const CMMI_PARENT_DOMAIN = {
  1: 'Data Management Strategy & Business Case',
  2: 'Data Governance',
  3: 'Data Quality',
  4: 'Data Operations & Lifecycle',
  5: 'Data Architecture & Technology',
  6: 'Process & Measurement',
}

function frameworkKeyFromValue(value) {
  const raw = String(value ?? '').trim().toLowerCase()
  if (!raw) return ''
  const normalized = raw.replaceAll(/[\s-]+/g, '_')
  if (normalized === 'ndi') return 'ndi'
  if (normalized === 'cmmi' || normalized === 'cmmi_dmm') return 'cmmi'
  return normalized
}

function frameworkLabelFromKey(key) {
  if (key === 'ndi') return 'NDI'
  if (key === 'cmmi') return 'CMMI'
  return String(key ?? '').replaceAll('_', ' ').toUpperCase()
}

function normalizeFrameworkOption(raw) {
  if (raw == null) return null
  if (typeof raw !== 'object') {
    const key = frameworkKeyFromValue(raw)
    return key ? { key, label: frameworkLabelFromKey(key) } : null
  }

  const key = frameworkKeyFromValue(
    raw.key ?? raw.code ?? raw.frameworkCode ?? raw.frameworkKey ?? raw.name ?? raw.frameworkName ?? raw.label,
  )
  if (!key) return null
  return {
    key,
    label: String(raw.label ?? raw.name ?? raw.frameworkName ?? raw.code ?? frameworkLabelFromKey(key)),
  }
}

function uniqueFrameworkOptions(options) {
  const result = []
  const seen = new Set()
  for (const raw of options ?? []) {
    const option = normalizeFrameworkOption(raw)
    if (!option || seen.has(option.key)) continue
    seen.add(option.key)
    result.push(option)
  }
  return result
}

function segmentFramework(seg) {
  const direct = frameworkKeyFromValue(
    seg?.frameworkKey ?? seg?.frameworkCode ?? seg?.framework ?? seg?.frameworkName,
  )
  if (direct) return direct

  const code = String(seg?.code ?? '')
  const title = String(seg?.title ?? '')
  if (code.startsWith('cmmi_') || title.startsWith('CMMI DMM ·')) return 'cmmi'
  if (code.startsWith('ndi_')) return 'ndi'
  return 'other'
}

function domainTitle(seg) {
  const t = String(seg?.title ?? '').replace(/^CMMI DMM ·\s*/u, '')
  if (/^(?:ndi|cmmi)[_\s-]/iu.test(t) || /^\d+(?:[\s._-]+\d+)+$/u.test(t)) {
    return titleFromQuestionText(seg) || fallbackDomainTitle(seg)
  }
  return t
}

function fallbackDomainTitle(seg) {
  const rawCode = String(seg?.code ?? seg?.segmentCode ?? seg?.domainCode ?? '').trim()
  const cmmiMatch = rawCode.toLowerCase().match(/^cmmi_(\d+)(?:_\d+)?$/u)
  if (cmmiMatch) return CMMI_PARENT_DOMAIN[cmmiMatch[1]] ?? 'Domain'

  const parts = rawCode
    .replace(/^(?:ndi|cmmi)[_\s-]*/iu, '')
    .split(/[_\s-]+/u)
    .filter(Boolean)
  const readable = parts
    .map((part) => (/^\d+$/u.test(part) ? part : `${part[0]?.toUpperCase() ?? ''}${part.slice(1).toLowerCase()}`))
    .join(' ')
  return readable ? `Domain ${readable}` : 'Domain'
}

function titleFromQuestionText(seg) {
  const code = String(seg?.code ?? seg?.segmentCode ?? '').split('_').filter(Boolean).at(-1)?.toUpperCase() ?? ''
  if (!code) return ''
  const escapedCode = code.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(
    `((?:Data|Business|Foundation|Reference|Metadata|Information|Change)[A-Za-z]*(?:[\\s&/-]+[A-Z]?[A-Za-z]+){0,8})\\s*\\(\\s*${escapedCode}\\s*\\)`,
    'i',
  )
  for (const question of seg?.questions ?? []) {
    const match = String(question?.text ?? '').replaceAll(/\s+/g, ' ').match(pattern)
    if (match?.[1]) return match[1].trim()
  }
  return ''
}

/** CMMI titles from backend look like "1.1 Data Management Strategy" after stripping the prefix. */
function cmmiDomainLines(seg) {
  if (segmentFramework(seg) !== 'cmmi') return null
  const raw = domainTitle(seg).trim()
  const m = raw.match(/^(\d+)\.(\d+)\s+(.+)$/u)
  if (!m) {
    return { domainLine: null, subdomainLine: raw }
  }
  const major = m[1]
  const subNum = `${m[1]}.${m[2]}`
  const name = m[3].trim()
  const parentName = CMMI_PARENT_DOMAIN[major] ?? `Domain ${major}`
  return {
    domainLine: `Domain ${major} — ${parentName}`,
    subdomainLine: `Sub-domain ${subNum} — ${name}`,
  }
}

function ndiLabel(score) {
  return (
    {
      0: 'Absence of capabilities',
      1: 'Establishing',
      2: 'Defined',
      3: 'Activated',
      4: 'Managed',
      5: 'Pioneer',
    }[score] ?? ''
  )
}

function cmmiLabel(score) {
  return (
    {
      1: 'Performed',
      2: 'Managed',
      3: 'Defined',
      4: 'Measured',
      5: 'Optimized',
    }[score] ?? ''
  )
}

function labelForQuestion(questionCode, score) {
  const code = String(questionCode ?? '')
  if (code.startsWith('ndi_')) return ndiLabel(score)
  if (code.startsWith('cmmi_')) return cmmiLabel(score)
  return ''
}

function labelForFramework(frameworkKey, rounded) {
  if (frameworkKey === 'ndi') return ndiLabel(rounded)
  if (frameworkKey === 'cmmi') return cmmiLabel(rounded)
  return ''
}

function clampInt(n, min, max) {
  return Math.min(max, Math.max(min, n))
}

function scoreOptionsForCode(questionCode) {
  const code = String(questionCode ?? '')
  if (code.startsWith('ndi_')) {
    return [0, 1, 2, 3, 4, 5].map((v) => ({
      value: v,
      label: `${v} — ${ndiLabel(v)}`,
    }))
  }
  if (code.startsWith('cmmi_')) {
    return [1, 2, 3, 4, 5].map((v) => ({
      value: v,
      label: `${v} — ${cmmiLabel(v)}`,
    }))
  }
  return [1, 2, 3, 4, 5].map((v) => ({ value: v, label: String(v) }))
}

function pathMismatchError(error) {
  const msg = String(error?.message ?? '')
  return (
    error?.status === 404 ||
    error?.status === 405 ||
    msg.includes(' 405 ') ||
    msg.includes('405 Method Not Allowed') ||
    msg.includes(' 404 ') ||
    msg.includes('404 Not Found')
  )
}

function permissionDeniedError(error) {
  const msg = String(error?.message ?? '').toLowerCase()
  return error?.status === 403 || msg.includes('not allowed') || msg.includes('forbidden')
}

function normalizeEvidenceItem(raw) {
  const id = raw?.id ?? raw?.evidenceId ?? raw?.evidence_id ?? null
  if (!id) return null
  return {
    id,
    evidenceId: id,
    fileName: raw?.fileName ?? raw?.originalFileName ?? raw?.evidenceFileName ?? raw?.name ?? '',
    fileUrl: raw?.fileUrl ?? raw?.downloadUrl ?? raw?.url ?? raw?.evidenceUrl ?? '',
    downloadUrl: raw?.downloadUrl ?? raw?.fileUrl ?? raw?.url ?? raw?.evidenceUrl ?? '',
    uploadedAt: raw?.uploadedAt ?? raw?.createdAt ?? raw?.created_at ?? '',
  }
}

function evidencesFromAnswer(raw) {
  const items = Array.isArray(raw?.evidences)
    ? raw.evidences.map(normalizeEvidenceItem).filter(Boolean)
    : []
  if (items.length > 0) return items
  const legacy = normalizeEvidenceItem({
    id: raw?.evidenceId ?? raw?.evidence?.id,
    fileName: raw?.evidenceFileName ?? raw?.evidence?.fileName ?? raw?.fileName,
    downloadUrl: raw?.evidenceUrl ?? raw?.evidence_url ?? raw?.evidence?.url,
    uploadedAt: raw?.evidence?.uploadedAt ?? raw?.evidence?.createdAt,
  })
  return legacy ? [legacy] : []
}

async function tryApiFetch(candidates, options) {
  let lastErr = null
  for (const candidate of candidates) {
    try {
      return await apiFetch(candidate.path, { ...(options ?? {}), method: candidate.method ?? options?.method })
    } catch (err) {
      lastErr = err
      if (!pathMismatchError(err)) throw err
    }
  }
  throw lastErr ?? new Error('Request failed')
}

function normalizeExistingAnswer(raw, fallbackCode = '') {
  const question = raw?.question && typeof raw.question === 'object' ? raw.question : null
  const questionCode =
    raw?.questionCode ?? raw?.code ?? raw?.question_code ?? question?.code ?? fallbackCode
  if (!questionCode) return null

  const score = raw?.score ?? raw?.answerScore ?? raw?.value ?? null
  const comment = raw?.comment ?? raw?.note ?? raw?.answerComment ?? raw?.label ?? ''
  const answered = raw?.answered ?? raw?.isAnswered ?? raw?.completed ?? raw?.complete ?? null
  const evidences = evidencesFromAnswer(raw)
  const firstEvidence = evidences[0] ?? null
  return {
    questionCode,
    score,
    comment,
    answered: typeof answered === 'boolean' ? answered : score !== null && score !== undefined,
    evidenceId: firstEvidence?.id ?? raw?.evidenceId ?? raw?.evidence?.id ?? null,
    evidenceUrl: firstEvidence?.downloadUrl ?? raw?.evidenceUrl ?? raw?.evidence_url ?? raw?.evidence?.url ?? '',
    evidenceFileName: firstEvidence?.fileName ?? raw?.evidenceFileName ?? raw?.evidence?.fileName ?? raw?.fileName ?? '',
    evidences,
    evidenceStaffRating: raw?.evidenceStaffRating ?? raw?.staffRating ?? raw?.evidence?.staffRating ?? null,
    answeredAt: raw?.answeredAt ?? raw?.answered_at ?? raw?.submittedAt ?? raw?.submitted_at ?? raw?.updatedAt ?? raw?.updated_at ?? '',
  }
}

function collectExistingAnswers(assessment) {
  const rows = []
  const addAnswers = (items, fallbackPrefix = '') => {
    for (const [index, item] of (items ?? []).entries()) {
      const row = normalizeExistingAnswer(item, item?.id ? `${fallbackPrefix}${item.id}` : '')
      if (row?.questionCode) rows.push(row)
      if (!row && item?.code && item?.score != null) {
        rows.push(normalizeExistingAnswer(item, `${fallbackPrefix}${index + 1}`))
      }
    }
  }

  for (const seg of assessment?.segments ?? []) {
    addAnswers(seg?.answers ?? seg?.questions, `${seg?.code ?? seg?.segmentCode ?? 'q'}-`)
    for (const sub of seg?.subDomains ?? seg?.subdomains ?? []) {
      addAnswers(sub?.answers ?? sub?.questions, `${seg?.code ?? 'q'}-`)
    }
  }

  for (const domain of assessment?.domains ?? assessment?.domainList ?? []) {
    addAnswers(domain?.answers ?? domain?.questions, `${domain?.code ?? domain?.domainCode ?? 'q'}-`)
    for (const sub of domain?.subDomains ?? domain?.subdomains ?? []) {
      addAnswers(sub?.answers ?? sub?.questions, `${domain?.code ?? 'q'}-`)
    }
  }

  return rows
}

function questionnaireFromAssessment(assessment) {
  const segments = []
  for (const [segIndex, seg] of (assessment?.segments ?? []).entries()) {
    const code = segmentCodeOf(seg) || `segment-${segIndex + 1}`
    const answers = [
      ...(seg?.answers ?? []),
      ...(seg?.questions ?? []),
      ...(seg?.subDomains ?? []).flatMap((sub) => sub?.answers ?? sub?.questions ?? []),
      ...(seg?.subdomains ?? []).flatMap((sub) => sub?.answers ?? sub?.questions ?? []),
    ]

    const questions = answers
      .map((ans, index) => {
        const questionCode = ans?.questionCode ?? ans?.code ?? ''
        if (!questionCode) return null
        return {
          code: questionCode,
          text: ans?.questionText ?? ans?.text ?? questionCode,
          sortOrder: index + 1,
        }
      })
      .filter(Boolean)

    if (questions.length === 0) continue
    segments.push({
      code,
      title: seg?.segmentTitle ?? seg?.title ?? code,
      sortOrder: seg?.sortOrder ?? segIndex + 1,
      parentSegmentCode: seg?.parentSegmentCode ?? null,
      maturityFrameworkCode: seg?.maturityFrameworkCode ?? null,
      weight: seg?.weight ?? null,
      questions,
    })
  }

  return { segments }
}

function segmentCodeOf(seg) {
  return String(seg?.code ?? seg?.segmentCode ?? seg?.domainCode ?? '').trim()
}

function questionCodeOf(question) {
  return String(question?.code ?? question?.questionCode ?? '').trim()
}

function segmentProgressSource(assessment) {
  const sources = [
    ...(assessment?.segments ?? []),
    ...(assessment?.domains ?? []),
    ...(assessment?.domainList ?? []),
  ]
  const result = new Map()

  for (const seg of sources) {
    const code = segmentCodeOf(seg)
    if (!code) continue

    const questionProgress = new Map()
    const addQuestionRows = (rows) => {
      for (const row of rows ?? []) {
        const normalized = normalizeExistingAnswer(row)
        if (normalized?.questionCode) questionProgress.set(normalized.questionCode, normalized)
      }
    }

    addQuestionRows(seg?.questions)
    addQuestionRows(seg?.answers)
    for (const sub of seg?.subDomains ?? seg?.subdomains ?? []) {
      addQuestionRows(sub?.questions)
      addQuestionRows(sub?.answers)
    }

    result.set(code, {
      answeredQuestions: seg?.answeredQuestions,
      totalQuestions: seg?.totalQuestions,
      progressPercent: seg?.progressPercent,
      complete: seg?.complete,
      score: seg?.score ?? seg?.domainScore,
      maturityLabel: seg?.maturityLabel ?? seg?.label,
      questionProgress,
    })
  }

  return result
}

function mergeQuestionnaireProgress(questionnaire, assessment) {
  if (!questionnaire || !assessment) return questionnaire
  const segmentsByCode = segmentProgressSource(assessment)

  return {
    ...questionnaire,
    segments: (questionnaire.segments ?? []).map((seg) => {
      const progress = segmentsByCode.get(segmentCodeOf(seg))
      if (!progress) return seg

      return {
        ...seg,
        answeredQuestions: progress.answeredQuestions ?? seg.answeredQuestions,
        totalQuestions: progress.totalQuestions ?? seg.totalQuestions,
        progressPercent: progress.progressPercent ?? seg.progressPercent,
        complete: progress.complete ?? seg.complete,
        score: progress.score ?? seg.score,
        maturityLabel: progress.maturityLabel ?? seg.maturityLabel,
        questions: (seg.questions ?? []).map((question) => {
          const qProgress = progress.questionProgress.get(questionCodeOf(question))
          if (!qProgress) return question
          return {
            ...question,
            answered: qProgress.answered,
          }
        }),
      }
    }),
  }
}

function pickAssessmentProgress(data, fallback = {}) {
  if (!data || typeof data !== 'object') return fallback
  const client = data.client && typeof data.client === 'object' ? data.client : null
  return {
    ...fallback,
    id: data.id ?? data.assessmentId ?? fallback.id,
    assessmentId: data.assessmentId ?? data.id ?? fallback.assessmentId,
    clientId: data.clientId ?? client?.id ?? fallback.clientId,
    clientName:
      data.clientName ??
      data.clientFullName ??
      data.assessment?.clientName ??
      data.assessment?.clientFullName ??
      client?.fullName ??
      client?.name ??
      fallback.clientName,
    clientEmail:
      data.clientEmail ??
      data.assessment?.clientEmail ??
      client?.email ??
      fallback.clientEmail,
    client: client ?? data.assessment?.client ?? fallback.client,
    status: data.status ?? fallback.status,
    globalStatus: data.globalStatus ?? data.status ?? fallback.globalStatus,
    frameworkStatus: Array.isArray(data.frameworkStatus) ? data.frameworkStatus : fallback.frameworkStatus,
    versionNumber: data.versionNumber ?? data.version ?? fallback.versionNumber ?? fallback.version,
    answeredQuestions: data.answeredQuestions ?? fallback.answeredQuestions,
    totalQuestions: data.totalQuestions ?? fallback.totalQuestions,
    progressPercent: data.progressPercent ?? fallback.progressPercent,
    complete: data.complete ?? fallback.complete,
    canSubmit: data.canSubmit ?? fallback.canSubmit,
    globalScore: data.globalScore ?? data.score ?? fallback.globalScore ?? fallback.score,
    globalAverageScore: data.globalAverageScore ?? data.global_average_score ?? fallback.globalAverageScore,
    globalMaturityLabel: data.globalMaturityLabel ?? data.maturityLabel ?? fallback.globalMaturityLabel,
    submittedAt: data.submittedAt ?? data.submitted_at ?? fallback.submittedAt,
  }
}

function assessmentIdFrom(data) {
  return data?.assessmentId ?? data?.id ?? data?.versionId ?? null
}

function parseVersionsResponse(raw) {
  if (Array.isArray(raw)) return raw
  if (raw?.content && Array.isArray(raw.content)) return raw.content
  if (raw?.items && Array.isArray(raw.items)) return raw.items
  if (raw?.versions && Array.isArray(raw.versions)) return raw.versions
  return []
}

function formatSubmittedDate(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('en-GB').format(date)
}

function versionStatusLabel(value) {
  const status = String(value ?? '').toUpperCase()
  if (status === 'SUBMITTED') return 'Submitted'
  if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'Current Assessment'
  return status || 'Current Assessment'
}

function versionSubmittedAt(row) {
  return (
    row?.submittedAt ??
    row?.raw?.submittedAt ??
    row?.raw?.submitted_at ??
    row?.raw?.lastSubmissionDate ??
    null
  )
}

function versionSubmittedText(row) {
  const status = versionStatusLabel(row?.status)
  const submittedAt = versionSubmittedAt(row)
  const formatted = formatSubmittedDate(submittedAt)
  if (status === 'Submitted') return formatted ? `Submitted at ${formatted}` : 'Not submitted yet'
  return 'Current Assessment'
}

function assessmentQuestions(questionnaire) {
  return (questionnaire?.segments ?? []).flatMap((segment) => segment?.questions ?? [])
}

function submitStateSignature(questions, answers = {}, evidences = {}) {
  return JSON.stringify(
    (questions ?? [])
      .map((question) => {
        const code = questionCodeOf(question)
        const answer = answers?.[code] ?? {}
        const evidence = evidences?.[code] ?? {}
        return {
          questionCode: code,
          answered: answer?.answered === true,
          score: answer?.answered === true && answer?.score !== null && answer?.score !== undefined ? Number(answer.score) : null,
          comment: answer?.comment ?? '',
          evidenceIds: (evidence?.items ?? []).map((item) => item.id ?? item.evidenceId),
          evidenceFileNames: (evidence?.items ?? []).map((item) => item.fileName ?? ''),
          pendingEvidenceFileNames: (evidence?.pendingFiles ?? (evidence?.pendingFile ? [evidence.pendingFile] : [])).map(
            (file) => file?.name ?? '',
          ),
          evidenceStaffRating: evidence?.staffRating ?? null,
        }
      })
      .sort((a, b) => a.questionCode.localeCompare(b.questionCode)),
  )
}

function pendingEvidenceEntries(evidences = {}) {
  return Object.entries(evidences).filter(
    ([, evidence]) => (evidence?.pendingFiles?.length ?? 0) > 0 || evidence?.pendingFile,
  )
}

function evidenceMapFromAssessment(assessment) {
  const nextEvidences = {}
  for (const ans of collectExistingAnswers(assessment)) {
    if ((ans.evidences?.length ?? 0) === 0 && !ans.evidenceId) continue
    const items = ans.evidences?.length
      ? ans.evidences
      : [
          {
            id: ans.evidenceId,
            evidenceId: ans.evidenceId,
            fileName: ans.evidenceFileName ?? '',
            downloadUrl: ans.evidenceUrl ?? '',
          },
        ]
    const first = items[0] ?? null
    nextEvidences[ans.questionCode] = {
      items,
      evidenceId: first?.id ?? first?.evidenceId ?? null,
      url: first?.downloadUrl ?? first?.fileUrl ?? ans.evidenceUrl ?? '',
      fileName: items.map((item) => item.fileName).filter(Boolean).join(', '),
      staffRating: ans.evidenceStaffRating ?? null,
    }
  }
  return nextEvidences
}

export function ClientHomePage({ staffMode = false, staffAssessmentId = null }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const role = roleFromAuth(auth)
  const isStaff = isStaffRole(role)
  const normalizedRole = normalizeRole(role)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [permissionDenied, setPermissionDenied] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [questionnaire, setQuestionnaire] = useState(null)
  const [assessmentMeta, setAssessmentMeta] = useState(null)
  const [answers, setAnswers] = useState(() => ({}))
  const [submitting, setSubmitting] = useState(false)
  const [submittedAssessment, setSubmittedAssessment] = useState(null)
  const [clientVersions, setClientVersions] = useState([])
  const [clientVersionsLoading, setClientVersionsLoading] = useState(false)
  const [clientVersionsError, setClientVersionsError] = useState('')
  const [clientVersionsOpen, setClientVersionsOpen] = useState(false)
  const [selectedClientVersionId, setSelectedClientVersionId] = useState(null)
  const [readOnlyVersion, setReadOnlyVersion] = useState(false)
  const [staffSubmitBaseline, setStaffSubmitBaseline] = useState('')
  const [clientHasSubmitChanges, setClientHasSubmitChanges] = useState(false)
  const [versionComment, setVersionComment] = useState('')

  const [framework, setFramework] = useState('ndi')
  const [activeSegmentCode, setActiveSegmentCode] = useState(null)
  const [showStatistics, setShowStatistics] = useState(false)
  const statisticsSectionRef = useRef(null)

  useEffect(() => {
    console.log('[ClientHomePage] resolved role for Export Assessment Report', {
      authRole: auth.role,
      storedRole: localStorage.getItem('pfe.auth.role'),
      role,
      isStaff,
    })
  }, [auth.role, role, isStaff])

  useEffect(() => {
    if (!showStatistics) return undefined
    const frame = window.requestAnimationFrame(() => {
      statisticsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [showStatistics])

  const [evidences, setEvidences] = useState(() => ({})) // questionCode -> { evidenceId, fileName, staffRating }
  const [, setSaveState] = useState('idle')
  const hydratedRef = useRef(false)
  const autosaveTimerRef = useRef(null)
  const lastSavedAnswersRef = useRef({})
  const submitInFlightRef = useRef(false)
  const lastSubmittedPayloadRef = useRef('')
  const apiAssessmentBase = staffMode ? '/api/admin/assessments' : '/api/client/assessments'

  async function loadClientVersions() {
    if (staffMode) return []
    setClientVersionsLoading(true)
    setClientVersionsError('')
    try {
      const raw = await apiFetch('/api/client/assessment-versions', {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      const rows = markLatestVersion(parseVersionsResponse(raw).map((row, index) => normalizeVersionRow(row, index)))
      setClientVersions(rows)
      return rows
    } catch (err) {
      setClientVersions([])
      if (pathMismatchError(err)) {
        setClientVersionsError('')
      } else {
        setClientVersionsError(EMPTY_ASSESSMENT_VERSIONS_MESSAGE)
      }
      return []
    } finally {
      setClientVersionsLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    async function run() {
      hydratedRef.current = false
      setError('')
      setPermissionDenied(false)
      setLoading(true)
      setStaffSubmitBaseline('')
      setClientHasSubmitChanges(false)
      setVersionComment('')
      lastSubmittedPayloadRef.current = ''
      try {
        const headers = { Authorization: `Bearer ${auth.token}` }
        if (staffMode && !staffAssessmentId) {
          throw new Error('Assessment id is required for staff editing.')
        }

        let q = null
        let meta = null
        let existing = null
        if (staffMode) {
          existing = await apiFetch(`${apiAssessmentBase}/${staffAssessmentId}`, { headers })
          q = await apiFetch(`${apiAssessmentBase}/${staffAssessmentId}/questionnaire`, { headers }).catch((err) => {
            if (!pathMismatchError(err)) throw err
            return questionnaireFromAssessment(existing)
          })
          meta = existing
        } else {
          const clientData = await Promise.all([
            apiFetch('/api/client/questionnaire', { headers }),
            apiFetch('/api/client/assessments', { method: 'POST', headers }),
          ])
          q = clientData[0]
          meta = clientData[1]
        }
        if (cancelled) return

        const initial = {}
        for (const seg of q?.segments ?? []) {
          for (const qu of seg?.questions ?? []) {
            initial[qu.code] = { score: null, comment: '' }
          }
        }

        // Hydrate existing saved answers/evidence immediately, including staff edit mode.
        const nextAnswers = { ...initial }
        const nextEvidences = {}
        if (!existing && meta?.assessmentId) {
          try {
            existing = await apiFetch(`${apiAssessmentBase}/${meta.assessmentId}`, { headers })
            if (cancelled) return
          } catch {
            // Ignore hydration failures; client can still proceed.
          }
        }
        for (const ans of collectExistingAnswers(existing)) {
          const answered = ans.answered === true
          nextAnswers[ans.questionCode] = {
            ...(nextAnswers[ans.questionCode] ?? {}),
            score: answered ? ans.score ?? null : null,
            answered,
            comment: answered ? ans.comment || labelForQuestion(ans.questionCode, ans.score ?? 0) : ans.comment ?? '',
            answeredAt: ans.answeredAt ?? '',
          }
        }
        Object.assign(nextEvidences, evidenceMapFromAssessment(existing))

        setQuestionnaire(mergeQuestionnaireProgress(q, existing ?? meta))
        const nextMeta = pickAssessmentProgress(existing, { ...(meta ?? {}), status: meta?.status ?? 'DRAFT' })
        setAssessmentMeta(nextMeta)
        setSelectedClientVersionId(nextMeta?.assessmentId ?? nextMeta?.id ?? null)
        setReadOnlyVersion(false)
        setAnswers(nextAnswers)
        setEvidences(nextEvidences)
        setStaffSubmitBaseline(staffMode ? submitStateSignature(assessmentQuestions(q), nextAnswers, nextEvidences) : '')
        lastSavedAnswersRef.current = Object.fromEntries(
          Object.entries(nextAnswers).map(([code, value]) => [
            code,
            JSON.stringify({
              score: value?.answered === true ? Number(value?.score) : null,
              answered: value?.answered === true,
              comment: value?.comment ?? '',
            }),
          ]),
        )
        hydratedRef.current = true
        if (!staffMode) {
          await loadClientVersions()
        }
      } catch (err) {
        if (!cancelled) {
          if (staffMode && permissionDeniedError(err)) {
            setPermissionDenied(true)
            setError('You do not have permission to edit this assessment.')
          } else {
            setPermissionDenied(false)
            setError(err?.message ?? 'Failed to load')
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [apiAssessmentBase, auth.token, staffAssessmentId, staffMode])

  const sortedSegments = useMemo(
    () =>
      (questionnaire?.segments ?? [])
        .slice()
        .sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0)),
    [questionnaire],
  )

  const frameworkOptions = useMemo(() => {
    const raw =
      questionnaire?.allowedFrameworks ??
      questionnaire?.frameworks ??
      assessmentMeta?.allowedFrameworks ??
      assessmentMeta?.frameworks ??
      []

    const inferred = sortedSegments.map((s) => segmentFramework(s)).filter((key) => key && key !== 'other')
    if (Array.isArray(raw) && raw.length > 0) {
      return uniqueFrameworkOptions([...raw, ...inferred])
    }

    const inferredOptions = uniqueFrameworkOptions(inferred)
    return inferredOptions.length > 0 ? inferredOptions : [{ key: 'ndi', label: 'NDI' }]
  }, [questionnaire, assessmentMeta, sortedSegments])

  const frameworkOptionSignature = frameworkOptions.map((option) => option.key).join('|')
  const selectedFrameworkOption = frameworkOptions.find((option) => option.key === framework) ?? frameworkOptions[0] ?? null

  useEffect(() => {
    // Force framework to an allowed value (and keep UI consistent when backend restricts access).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFramework((cur) => {
      if (frameworkOptions.some((option) => option.key === cur)) return cur
      return frameworkOptions[0]?.key ?? 'ndi'
    })
  }, [frameworkOptions, frameworkOptionSignature])

  const frameworkSegments = useMemo(() => {
    return sortedSegments.filter((s) => segmentFramework(s) === framework)
  }, [sortedSegments, framework])

  useEffect(() => {
    if (!frameworkSegments.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveSegmentCode(null)
      return
    }
    setActiveSegmentCode((current) => {
      if (current && frameworkSegments.some((s) => s.code === current)) return current
      return frameworkSegments[0].code
    })
  }, [frameworkSegments])

  const activeSegment = useMemo(
    () => frameworkSegments.find((s) => s.code === activeSegmentCode) ?? null,
    [frameworkSegments, activeSegmentCode],
  )

  const frameworkQuestions = useMemo(
    () => frameworkSegments.flatMap((s) => s.questions ?? []),
    [frameworkSegments],
  )

  const allQuestions = useMemo(
    () => assessmentQuestions({ segments: sortedSegments }),
    [sortedSegments],
  )

  function submitQuestions() {
    if (staffMode) {
      return allQuestions.filter(questionAnswered)
    }

    const selectedCodes = new Set(frameworkQuestions.map((question) => questionCodeOf(question)).filter(Boolean))
    const selectedAnswered = frameworkQuestions.filter(questionAnswered).length
    const allAnswered = allQuestions.filter(questionAnswered).length

    // Some backend payloads have a question with incomplete framework metadata. When the backend says
    // the assessment is complete, submit every answered questionnaire question so that hidden rows are not dropped.
    if (backendCanSubmit && allAnswered > selectedAnswered) {
      return allQuestions.filter((question) => {
        const code = questionCodeOf(question)
        return code && (selectedCodes.has(code) || questionAnswered(question))
      })
    }

    return frameworkQuestions
  }

  function questionAnswered(question) {
    const code = questionCodeOf(question)
    return answers?.[code]?.answered === true || question?.answered === true
  }

  const isComplete = assessmentMeta?.complete === true
  const backendCanSubmit = assessmentMeta?.canSubmit === true
  const canSubmit = backendCanSubmit
  const staffCurrentSubmitSignature = useMemo(
    () => (staffMode ? submitStateSignature(allQuestions, answers, evidences) : ''),
    [allQuestions, answers, evidences, staffMode],
  )
  const staffHasSubmitChanges =
    staffMode &&
    Boolean(staffSubmitBaseline) &&
    staffCurrentSubmitSignature !== staffSubmitBaseline
  const staffCanSubmit =
    staffMode &&
    !readOnlyVersion &&
    staffHasSubmitChanges &&
    allQuestions.length > 0 &&
    allQuestions.every(questionAnswered)
  const frameworkStatus = Array.isArray(assessmentMeta?.frameworkStatus) ? assessmentMeta.frameworkStatus : []
  const submittedFrameworkLabels = frameworkStatus
    .filter((item) => String(item?.frameworkStatus ?? '').toUpperCase() === 'SUBMITTED')
    .map((item) => item.frameworkCode)
  const draftFrameworkLabels = frameworkStatus
    .filter((item) => String(item?.frameworkStatus ?? '').toUpperCase() !== 'SUBMITTED')
    .map((item) => item.frameworkCode)
  const submitBlockedMessage =
    submittedFrameworkLabels.length > 0 && draftFrameworkLabels.length > 0
      ? `${submittedFrameworkLabels.join(', ')} is already submitted. Please complete ${draftFrameworkLabels.join(', ')} before submitting the global assessment.`
      : 'Answer every question in every framework to enable submit.'

  const frameworkProgress = useMemo(() => {
    const total = frameworkQuestions.length
    const answered = frameworkQuestions.filter(questionAnswered).length
    const rows = frameworkSegments
      .map((seg) => ({
        score: segmentAverage(seg),
        weight: segmentWeight(seg),
      }))
      .filter((row) => row.score !== null && Number.isFinite(Number(row.score)))
    const weightedTotal = rows.reduce((sum, row) => sum + Number(row.score) * (row.weight ?? 1), 0)
    const totalWeight = rows.reduce((sum, row) => sum + (row.weight ?? 1), 0)
    const avg = totalWeight > 0 ? Math.round((weightedTotal / totalWeight) * 100) / 100 : null

    console.debug('[Assessment AVG][client]', {
      framework,
      displayedFrameworkAvg: avg,
      formula: 'weighted average of official domain scores for active framework',
      domainScores: frameworkSegments.map((seg) => ({
        code: seg.code,
        title: domainTitle(seg),
        score: segmentAverage(seg),
        weight: segmentWeight(seg) ?? 1,
      })),
    })

    return { total, answered, avg }
  }, [answers, frameworkQuestions, frameworkSegments])

  const activeSegmentScoring = useMemo(() => {
    if (!activeSegment) return { avg: null, rounded: null, label: '' }
    const score = segmentAverage(activeSegment)
    if (score === null || score === undefined) return { avg: null, rounded: null, label: '' }
    const rounded = Math.round(score)
    const r = framework === 'ndi' ? clampInt(rounded, 0, 5) : clampInt(rounded, 0, 5)
    const label = framework === 'cmmi' && r === 0 ? '' : labelForFramework(framework, r === 0 ? 1 : r)
    return { avg: score, rounded: r, label }
  }, [activeSegment, answers, framework])

  const domainAnalysisItems = useMemo(() => {
    return frameworkSegments.map((seg) => {
      const avg = segmentAverage(seg)
      const lines = cmmiDomainLines(seg)
      const full = lines ? lines.subdomainLine : domainTitle(seg)
      const mainLine = full.includes('—') ? full.split('—')[0].trim() : full
      const shortTitle = mainLine.length > 44 ? `${mainLine.slice(0, 42)}…` : mainLine
      const subtitle = full.length > 30 ? `${full.slice(0, 28)}…` : full
      return {
        key: seg.code,
        shortTitle,
        subtitle,
        score: avg,
        weight: segmentWeight(seg),
      }
    })
  }, [frameworkSegments, answers])

  const radarSummary = useMemo(() => {
    const withScores = domainAnalysisItems
      .filter((r) => r.score != null && Number.isFinite(Number(r.score)))
    if (!withScores.length) {
      return { value: null, bandLabel: '' }
    }
    const weightedTotal = withScores.reduce((sum, row) => sum + Number(row.score) * (row.weight ?? 1), 0)
    const totalWeight = withScores.reduce((sum, row) => sum + (row.weight ?? 1), 0)
    const mean = totalWeight > 0 ? Math.round((weightedTotal / totalWeight) * 100) / 100 : null
    const rounded = clampInt(Math.round(mean), 0, 5)
    return {
      value: mean,
      bandLabel: framework === 'cmmi' && rounded === 0 ? '' : labelForFramework(framework, rounded === 0 ? 1 : rounded),
    }
  }, [domainAnalysisItems, framework])

  const segmentQuestionPoints = useMemo(() => {
    if (!activeSegment) return []
    const qs = [...(activeSegment.questions ?? [])].sort(
      (a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0),
    )
    return qs.map((q, i) => {
      const raw = answers?.[q.code]?.score
      const score =
        raw === null || raw === undefined || !Number.isFinite(Number(raw)) ? null : Number(raw)
      const t = String(q.text ?? '')
      const hint = t.length > 100 ? `${t.slice(0, 100)}…` : t
      return {
        key: q.code,
        shortLabel: `Q${i + 1}`,
        label: q.code,
        hint,
        score,
      }
    })
  }, [activeSegment, answers])

  const domainScoreboard = useMemo(() => {
    const rows = frameworkSegments.map((seg) => {
      const avg = segmentAverage(seg)
      const rounded =
        avg === null ? null : Math.round(avg)
      const r =
        rounded === null ? null : framework === 'ndi' ? clampInt(rounded, 0, 5) : clampInt(rounded, 0, 5)
      const label =
        r === null ? '' : framework === 'cmmi' && r === 0 ? '' : labelForFramework(framework, r === 0 ? 1 : r)

      const title = (() => {
        const lines = cmmiDomainLines(seg)
        if (lines) return lines.subdomainLine
        return domainTitle(seg)
      })()

      return {
        code: seg.code,
        title,
        complete: (seg.questions ?? []).length > 0 && (seg.questions ?? []).every(questionAnswered),
        answeredQuestions: (seg.questions ?? []).filter(questionAnswered).length,
        totalQuestions: (seg.questions ?? []).length,
        avg,
        averageScore: segmentDisplayAverage(seg),
        label,
      }
    })

    const totalAvg = frameworkProgress.avg
    const totalRounded = framework === 'ndi' ? clampInt(Math.round(totalAvg), 0, 5) : clampInt(Math.round(totalAvg), 0, 5)
    const totalLabel =
      totalAvg === null || Number.isNaN(totalRounded)
        ? ''
        : framework === 'cmmi' && totalRounded === 0
          ? ''
          : labelForFramework(framework, totalRounded === 0 ? 1 : totalRounded)

    return { rows, totalAvg, totalLabel }
  }, [frameworkSegments, answers, framework, frameworkProgress.avg])

  function setScore(questionCode, score) {
    if (readOnlyVersion) return
    const n = Number(score)
    const label = labelForQuestion(questionCode, n)
    setSubmittedAssessment(null)
    if (!staffMode) {
      setClientHasSubmitChanges(true)
      setAssessmentMeta((prev) => ({ ...(prev ?? {}), status: 'IN_PROGRESS' }))
    }
    setAnswers((prev) => ({
      ...prev,
      [questionCode]: {
        ...(prev[questionCode] ?? {}),
        score: Number.isFinite(n) ? n : null,
        answered: true,
        comment: label,
      },
    }))
  }

  function setComment(questionCode, comment) {
    if (readOnlyVersion) return
    setSubmittedAssessment(null)
    if (!staffMode) {
      setClientHasSubmitChanges(true)
      setAssessmentMeta((prev) => ({ ...(prev ?? {}), status: 'IN_PROGRESS' }))
    }
    setAnswers((prev) => ({
      ...prev,
      [questionCode]: { ...(prev[questionCode] ?? {}), comment },
    }))
  }

  function segmentProgress(seg) {
    const questions = seg?.questions ?? []
    return {
      done: questions.filter(questionAnswered).length,
      total: questions.length,
    }
  }

  function segmentAverage(seg) {
    const qs = seg?.questions ?? []
    if (!qs.length) return 0
    if (!qs.every(questionAnswered)) return 0
    const values = qs.filter(questionAnswered).map((q) => {
      const v = answers?.[q.code]?.score
      return v === null || v === undefined ? null : Number(v)
    }).filter((value) => value !== null && Number.isFinite(value))
    if (values.length === 0) {
      return seg?.score !== null && seg?.score !== undefined ? Number(seg.score) : null
    }
    const minScore = Math.min(...values)
    return Math.round(minScore * 100) / 100
  }

  function segmentDisplayAverage(seg) {
    const values = (seg?.questions ?? [])
      .map((q) => {
        const code = questionCodeOf(q)
        const raw = answers?.[code]?.score
        return raw === null || raw === undefined || !Number.isFinite(Number(raw)) ? null : Number(raw)
      })
      .filter((value) => value !== null)

    if (!values.length) return null
    return Math.round((values.reduce((sum, value) => sum + value, 0) / values.length) * 100) / 100
  }

  function segmentWeight(seg) {
    const raw = seg?.weight ?? seg?.domainWeight ?? seg?.frameworkWeight ?? seg?.scoreWeight
    const value = Number(raw)
    return Number.isFinite(value) && value > 0 ? value : null
  }

  const averageFrameworkScore = useMemo(() => {
    const rows = frameworkSegments
      .map((seg) => ({
        score: segmentDisplayAverage(seg),
        weight: segmentWeight(seg),
      }))
      .filter((row) => row.score !== null && Number.isFinite(Number(row.score)))

    if (rows.length === 0) return null

    const weightedTotal = rows.reduce((sum, row) => sum + Number(row.score) * (row.weight ?? 1), 0)
    const totalWeight = rows.reduce((sum, row) => sum + (row.weight ?? 1), 0)

    return totalWeight > 0 ? Math.round((weightedTotal / totalWeight) * 100) / 100 : null
  }, [answers, frameworkSegments])

  async function saveDraftAnswers(answersToSave) {
    if (!assessmentMeta?.assessmentId || answersToSave.length === 0) return
    const currentAssessmentId = assessmentMeta.assessmentId
    const headers = { Authorization: `Bearer ${auth.token}` }
    const payload = { answers: answersToSave }

    try {
      const saveResponse = await tryApiFetch(
        [
          { method: 'PATCH', path: `${apiAssessmentBase}/${currentAssessmentId}/answers` },
          { method: 'PUT', path: `${apiAssessmentBase}/${currentAssessmentId}/answers` },
          { method: 'POST', path: `${apiAssessmentBase}/${currentAssessmentId}/answers` },
          { method: 'PATCH', path: `${apiAssessmentBase}/${currentAssessmentId}` },
          { method: 'PUT', path: `${apiAssessmentBase}/${currentAssessmentId}` },
        ],
        { headers, body: JSON.stringify(payload) },
      )
      const nextAssessmentId = assessmentIdFrom(saveResponse) ?? currentAssessmentId
      return (await fetchCurrentAssessment(nextAssessmentId).catch(() => null)) ?? saveResponse
    } catch (err) {
      if (!pathMismatchError(err)) throw err
    }

    let latest = null
    for (const answer of answersToSave) {
      const encoded = encodeURIComponent(answer.questionCode)
      latest = await tryApiFetch(
        [
          { method: 'PATCH', path: `${apiAssessmentBase}/${currentAssessmentId}/answers/${encoded}` },
          { method: 'PUT', path: `${apiAssessmentBase}/${currentAssessmentId}/answers/${encoded}` },
          { method: 'POST', path: `${apiAssessmentBase}/${currentAssessmentId}/answers/${encoded}` },
        ],
        { headers, body: JSON.stringify(answer) },
      )
    }
    const nextAssessmentId = assessmentIdFrom(latest) ?? currentAssessmentId
    return (await fetchCurrentAssessment(nextAssessmentId).catch(() => null)) ?? latest
  }

  async function fetchCurrentAssessment(assessmentId = assessmentMeta?.assessmentId) {
    if (!assessmentId) return null
    return apiFetch(`${apiAssessmentBase}/${assessmentId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  }

  function applyAssessmentProgress(snapshot) {
    if (!snapshot || typeof snapshot !== 'object') return
    setAssessmentMeta((prev) => pickAssessmentProgress(snapshot, prev ?? {}))
    setQuestionnaire((prev) => mergeQuestionnaireProgress(prev, snapshot))

    const persistedAnswers = collectExistingAnswers(snapshot)
    if (persistedAnswers.length === 0) return

    setAnswers((prev) => {
      const next = { ...prev }
      for (const ans of persistedAnswers) {
        const answered = ans.answered === true
        next[ans.questionCode] = {
          ...(next[ans.questionCode] ?? {}),
          score: answered ? ans.score ?? null : null,
          answered,
          comment: answered ? ans.comment || labelForQuestion(ans.questionCode, ans.score ?? 0) : ans.comment ?? '',
          answeredAt: ans.answeredAt ?? next[ans.questionCode]?.answeredAt ?? '',
        }

        lastSavedAnswersRef.current[ans.questionCode] = JSON.stringify({
          score: answered ? Number(ans.score) : null,
          answered,
          comment: next[ans.questionCode].comment ?? '',
        })
      }
      return next
    })
  }

  function applyVersionSnapshot(snapshot, versionRow) {
    if (!snapshot || typeof snapshot !== 'object') return
    const nextMeta = pickAssessmentProgress(snapshot, assessmentMeta ?? {})
    const baseQuestionnaire = mergeQuestionnaireProgress(questionnaire, snapshot)
    const initial = {}
    for (const seg of baseQuestionnaire?.segments ?? []) {
      for (const qu of seg?.questions ?? []) {
        initial[qu.code] = { score: null, comment: '' }
      }
    }

    const nextAnswers = { ...initial }
    const nextEvidences = {}
    for (const ans of collectExistingAnswers(snapshot)) {
      const answered = ans.answered === true
      nextAnswers[ans.questionCode] = {
        ...(nextAnswers[ans.questionCode] ?? {}),
        score: answered ? ans.score ?? null : null,
        answered,
        comment: answered ? ans.comment || labelForQuestion(ans.questionCode, ans.score ?? 0) : ans.comment ?? '',
        answeredAt: ans.answeredAt ?? '',
      }
    }
    Object.assign(nextEvidences, evidenceMapFromAssessment(snapshot))

    setQuestionnaire(baseQuestionnaire)
    setAssessmentMeta(nextMeta)
    setAnswers(nextAnswers)
    setEvidences(nextEvidences)
    setSubmittedAssessment(isSubmittedAssessment(snapshot) ? snapshot : null)
    setSelectedClientVersionId(assessmentIdFrom(snapshot) ?? versionRow?.id ?? null)
    setReadOnlyVersion(!versionRow?.isLatest)
    setClientHasSubmitChanges(false)
    lastSavedAnswersRef.current = Object.fromEntries(
      Object.entries(nextAnswers).map(([code, value]) => [
        code,
        JSON.stringify({
          score: value?.answered === true ? Number(value?.score) : null,
          answered: value?.answered === true,
          comment: value?.comment ?? '',
        }),
      ]),
    )
    hydratedRef.current = true
    setSaveState(versionRow?.isLatest ? 'idle' : 'readonly')
  }

  async function onSelectClientVersion(versionRow) {
    if (!versionRow?.id) return
    setError('')
    try {
      const snapshot = await apiFetch(`/api/client/assessment-versions/${versionRow.id}`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      applyVersionSnapshot(snapshot, versionRow)
      setClientVersionsOpen(false)
    } catch (err) {
      setError(err?.message ?? 'Could not load assessment version')
    }
  }

  useEffect(() => {
    if (!hydratedRef.current || !assessmentMeta?.assessmentId) return undefined
    if (readOnlyVersion) return undefined

    const changes = allQuestions
      .map((q) => {
        const current = answers?.[q.code] ?? {}
        const answered = current.answered === true
        if (!answered && !String(current.comment ?? '').trim()) return null

        const snapshot = JSON.stringify({
          score: answered ? Number(current.score) : null,
          answered,
          comment: current.comment ?? '',
        })
        if (lastSavedAnswersRef.current[q.code] === snapshot) return null

        return {
          questionCode: q.code,
          score: answered ? Number(current.score) : null,
          answered,
          comment: current.comment ?? '',
          snapshot,
        }
      })
      .filter(Boolean)

    if (changes.length === 0) return undefined

    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
    setSaveState('saving')
    autosaveTimerRef.current = window.setTimeout(async () => {
      try {
        const snapshot = await saveDraftAnswers(
          changes.map(({ questionCode, score, answered, comment }) => ({
            questionCode,
            score,
            answered,
            comment,
          })),
        )
        const beforeId = assessmentMeta?.assessmentId
        applyAssessmentProgress(snapshot)
        const afterId = assessmentIdFrom(snapshot)
        if (!staffMode && afterId && String(afterId) !== String(beforeId)) {
          await loadClientVersions()
          setSelectedClientVersionId(afterId)
        }
        for (const change of changes) {
          lastSavedAnswersRef.current[change.questionCode] = change.snapshot
        }
        setSaveState('saved')
      } catch (err) {
        setSaveState('error')
        setError(err?.message ?? 'Current assessment autosave failed')
      }
    }, 700)

    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
    }
  }, [allQuestions, answers, assessmentMeta?.assessmentId, readOnlyVersion, staffMode])

  async function onSubmit() {
    if (submitInFlightRef.current) return
    if (!assessmentMeta?.assessmentId) return
    if (readOnlyVersion) return
    if (staffMode && !staffHasSubmitChanges) return
    const submitAllowed = staffMode ? staffCanSubmit : clientSubmitAllowed
    if (!submitAllowed) {
      setError(submitBlockedMessage)
      return
    }
    setError('')
    submitInFlightRef.current = true
    setSubmitting(true)
    try {
      const questionsToSubmit = submitQuestions()
      const missingQuestions = questionsToSubmit.filter((q) => {
        const code = questionCodeOf(q)
        const rawScore = answers?.[code]?.score
        return !code || answers?.[code]?.answered !== true || rawScore === null || rawScore === undefined || Number.isNaN(Number(rawScore))
      })
      if (missingQuestions.length > 0) {
        const missingLabels = missingQuestions
          .slice(0, 3)
          .map((q) => questionCodeOf(q) || q?.text || 'Question')
          .join(', ')
        throw new Error(`Please score every question before submitting. Missing: ${missingLabels}`)
      }

      const trimmedVersionComment = versionComment.trim()
      const payload = {
        answers: questionsToSubmit.map((q) => {
          const code = questionCodeOf(q)
          return {
            questionCode: code,
            score: Number(answers?.[code]?.score),
            answered: true,
            comment: answers?.[code]?.comment ?? '',
          }
        }),
      }
      if (trimmedVersionComment) {
        payload.versionComment = trimmedVersionComment
      }
      if ((staffMode && staffHasSubmitChanges) || (!staffMode && clientPendingVersionSubmit)) {
        payload.forceNewVersion = true
      }
      const payloadSignature = JSON.stringify(payload)
      const submitSignature = staffMode
        ? JSON.stringify({ answersAndEvidence: staffCurrentSubmitSignature, versionComment: trimmedVersionComment })
        : payloadSignature
      if (lastSubmittedPayloadRef.current === submitSignature) return

      let targetAssessmentId = assessmentMeta.assessmentId
      if (!staffMode && clientPendingVersionSubmit && !canSubmit) {
        if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
        const draftSnapshot = await saveDraftAnswers(payload.answers)
        if (draftSnapshot) {
          applyAssessmentProgress(draftSnapshot)
          targetAssessmentId = assessmentIdFrom(draftSnapshot) ?? targetAssessmentId
        }
      }

      const submitResponse = await apiFetch(`${apiAssessmentBase}/${targetAssessmentId}/submit`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: JSON.stringify(payload),
      })

      const submittedAssessmentId = assessmentIdFrom(submitResponse) ?? targetAssessmentId
      if (staffMode) {
        for (const [questionCode, evidence] of pendingEvidenceEntries(evidences)) {
          const score = Number(answers?.[questionCode]?.score)
          const form = new FormData()
          form.append('score', String(score))
          for (const file of evidence.pendingFiles ?? (evidence.pendingFile ? [evidence.pendingFile] : [])) {
            form.append('file', file)
          }
          await apiFetchFormData(
            `${apiAssessmentBase}/${submittedAssessmentId}/answers/${encodeURIComponent(questionCode)}/evidence`,
            {
              method: 'POST',
              headers: { Authorization: `Bearer ${auth.token}` },
              body: form,
            },
          )
        }
      }

      const assessment = await apiFetch(`${apiAssessmentBase}/${submittedAssessmentId}`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      const nextEvidences = evidenceMapFromAssessment(assessment)
      setSubmittedAssessment(assessment)
      setAssessmentMeta((prev) => pickAssessmentProgress(assessment, { ...(prev ?? {}), status: 'SUBMITTED' }))
      setQuestionnaire((prev) => mergeQuestionnaireProgress(prev, assessment))
      setEvidences(nextEvidences)
      setSaveState('saved')
      if (staffMode) {
        const nextBaseline = submitStateSignature(allQuestions, answers, nextEvidences)
        lastSubmittedPayloadRef.current = nextBaseline
        setStaffSubmitBaseline(nextBaseline)
      } else {
        lastSubmittedPayloadRef.current = submitSignature
      }
      setClientHasSubmitChanges(false)
      setVersionComment('')
      if (!staffMode) {
        await loadClientVersions()
      }
    } catch (err) {
      setError(err?.message ?? 'Submission failed')
    } finally {
      submitInFlightRef.current = false
      setSubmitting(false)
    }
  }

  async function uploadEvidence(questionCode, file) {
    return uploadEvidences(questionCode, file ? [file] : [])
  }

  async function uploadEvidences(questionCode, files) {
    if (!assessmentMeta?.assessmentId) throw new Error('Assessment not ready')
    if (readOnlyVersion) throw new Error('This assessment version is read-only')
    const uploadFiles = Array.from(files ?? []).filter(Boolean)
    if (uploadFiles.length === 0) return
    const currentScore = answers?.[questionCode]?.score
    if (answers?.[questionCode]?.answered !== true || currentScore === null || currentScore === undefined) {
      throw new Error('Select a score before uploading evidence.')
    }
    setSubmittedAssessment(null)
    setClientHasSubmitChanges(true)
    setAssessmentMeta((prev) => ({ ...(prev ?? {}), status: 'IN_PROGRESS' }))
    const scoreToSend = Number(currentScore)
    const form = new FormData()
    form.append('score', String(scoreToSend))
    for (const file of uploadFiles) {
      form.append('file', file)
    }
    const res = await apiFetchFormData(
      `${apiAssessmentBase}/${assessmentMeta.assessmentId}/answers/${encodeURIComponent(questionCode)}/evidence`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: form,
      },
    )
    const uploaded = Array.isArray(res) ? res : [res]
    setEvidences((prev) => ({
      ...prev,
      [questionCode]: {
        ...(prev[questionCode] ?? {}),
        items: [
          ...(prev[questionCode]?.items ?? []),
          ...uploaded
            .map((item, index) =>
              normalizeEvidenceItem({
                id: item?.evidenceId ?? item?.id,
                fileName: item?.originalFileName ?? uploadFiles[index]?.name,
                uploadedAt: item?.createdAt,
              }),
            )
            .filter(Boolean),
        ],
        evidenceId: uploaded[0]?.evidenceId ?? uploaded[0]?.id ?? prev[questionCode]?.evidenceId ?? null,
        fileName: [
          ...(prev[questionCode]?.items ?? []),
          ...uploaded.map((item, index) => ({ fileName: item?.originalFileName ?? uploadFiles[index]?.name ?? '' })),
        ]
          .map((item) => item.fileName)
          .filter(Boolean)
          .join(', '),
        staffRating: uploaded[0]?.staffRating ?? prev[questionCode]?.staffRating ?? null,
      },
    }))
    const nextAssessmentId = assessmentIdFrom(res) ?? assessmentIdFrom(uploaded[0]) ?? assessmentMeta.assessmentId
    const fresh = await fetchCurrentAssessment(nextAssessmentId).catch(() => null)
    applyAssessmentProgress(fresh ?? res)
  }

  async function downloadEvidenceFile(evidence) {
    const evidenceId = evidence?.id ?? evidence?.evidenceId
    if (!evidenceId) return
    const res = await fetch(`${apiAssessmentBase.replace('/assessments', '')}/evidences/${evidenceId}/download`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!res.ok) {
      throw new Error('Download failed')
    }
    const blob = await res.blob()
    const cd = res.headers.get('content-disposition') ?? ''
    const m = cd.match(/filename="?([^";]+)"?/i)
    const fileName = m?.[1] ?? evidence?.fileName ?? `evidence-${evidenceId}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  }

  async function downloadAllEvidencesForQuestion(questionCode) {
    const items = evidences?.[questionCode]?.items ?? []
    if (items.length === 0) return
    for (const item of items) {
      await downloadEvidenceFile(item)
    }
  }

  const canDeleteEvidence =
    !readOnlyVersion &&
    (!staffMode || normalizedRole === 'CONSULTANT' || normalizedRole === 'MANAGER')

  async function confirmDeleteEvidence() {
    if (!pendingDelete?.id) return
    const evidenceId = pendingDelete.id
    const questionCode = pendingDelete.questionCode
    setDeletingId(evidenceId)
    try {
      await deleteEvidence(evidenceId, auth.token, { staff: staffMode })
      setEvidences((prev) => {
        const current = prev?.[questionCode]
        if (!current) return prev
        const items = (current.items ?? []).filter(
          (item) => String(item.id ?? item.evidenceId) !== String(evidenceId),
        )
        const first = items[0] ?? null
        return {
          ...prev,
          [questionCode]: {
            ...current,
            items,
            evidenceId: first?.id ?? first?.evidenceId ?? null,
            url: first?.downloadUrl ?? first?.fileUrl ?? '',
            fileName: items.map((item) => item.fileName).filter(Boolean).join(', '),
          },
        }
      })
      setPendingDelete(null)
    } catch (err) {
      setError(err?.message ?? 'Failed to delete evidence')
    } finally {
      setDeletingId(null)
    }
  }

  const selectedClientVersion = clientVersions.find((row) => String(row.id) === String(selectedClientVersionId))
  const selectedFrameworkStatus = frameworkStatus.find(
    (item) => frameworkKeyFromValue(item?.frameworkCode) === frameworkKeyFromValue(framework),
  )
  const clientWorkflowStatus =
    assessmentMeta?.status ??
    submittedAssessment?.status ??
    selectedClientVersion?.raw?.status ??
    selectedClientVersion?.status ??
    'DRAFT'
  const staffEffectiveStatus =
    selectedFrameworkStatus?.frameworkStatus ??
    selectedClientVersion?.status ??
    selectedClientVersion?.raw?.status ??
    submittedAssessment?.globalStatus ??
    submittedAssessment?.status ??
    assessmentMeta?.globalStatus ??
    assessmentMeta?.status ??
    'DRAFT'
  const effectiveStatus = staffMode ? staffEffectiveStatus : clientWorkflowStatus
  const normalizedEffectiveStatus = String(effectiveStatus ?? '').toUpperCase()
  const currentStatus = normalizedEffectiveStatus === 'SUBMITTED' ? 'Submitted' : 'Current Assessment'
  const isSubmitted = normalizedEffectiveStatus === 'SUBMITTED'
  const clientHasSubmittedHistory =
    !staffMode && clientVersions.some((row) => String(row?.status ?? row?.raw?.status ?? '').toUpperCase() === 'SUBMITTED')
  const currentVersionNumber = Number(assessmentMeta?.versionNumber ?? assessmentMeta?.version ?? selectedClientVersion?.versionNumber ?? 1)
  const clientPendingVersionSubmit =
    !staffMode &&
    !readOnlyVersion &&
    clientHasSubmittedHistory &&
    (clientHasSubmitChanges || (!isSubmitted && currentVersionNumber > 1))
  const clientAllQuestionsAnswered = !staffMode && allQuestions.length > 0 && allQuestions.every(questionAnswered)
  const clientSubmitAllowed =
    !staffMode &&
    !readOnlyVersion &&
    (canSubmit || (clientPendingVersionSubmit && clientAllQuestionsAnswered)) &&
    (!isSubmitted || clientPendingVersionSubmit)
  const canShowVersionComment =
    !readOnlyVersion &&
    ((staffMode && (role === 'MANAGER' || role === 'CONSULTANT') && staffHasSubmitChanges) ||
      (!staffMode && clientPendingVersionSubmit && clientSubmitAllowed))
  const staffClientName =
    assessmentMeta?.clientName ??
    assessmentMeta?.clientFullName ??
    assessmentMeta?.assessment?.clientName ??
    assessmentMeta?.assessment?.clientFullName ??
    assessmentMeta?.client?.fullName ??
    assessmentMeta?.client?.name ??
    assessmentMeta?.clientEmail ??
    'Client'
  const staffClientEmail =
    assessmentMeta?.clientEmail ??
    assessmentMeta?.assessment?.clientEmail ??
    assessmentMeta?.client?.email ??
    ''
  const staffAssessmentYear = assessmentMeta?.year ?? '—'
  const staffAssessmentVersion = assessmentMeta?.versionNumber ?? assessmentMeta?.version ?? '—'
  const footerStateLabel = isSubmitted ? 'Submitted' : 'Current Assessment'
  const staffFooterMessage = staffHasSubmitChanges
    ? 'Staff edit mode: changes saved. · Submit to validate'
    : isSubmitted
      ? 'Staff edit mode: no changes to submit. · Submitted saved'
      : 'Staff edit mode: no changes to submit. · Current assessment saved'
  const clientFooterMessage = clientPendingVersionSubmit
    ? 'Changes saved. · Submit to create a new version'
    : isSubmitted
      ? 'Assessment already submitted. · Submitted'
      : `Current assessment saved. · ${footerStateLabel}`
  const canExportPdf = isStaff && isSubmitted
  const latestSubmissionDate = (() => {
    const submittedDates = clientVersions
      .filter((row) => versionStatusLabel(row.status) === 'Submitted')
      .map(versionSubmittedAt)
      .filter(Boolean)
      .map((value) => new Date(value))
      .filter((date) => !Number.isNaN(date.getTime()))
      .sort((a, b) => b.getTime() - a.getTime())

    if (submittedDates.length > 0) {
      return formatSubmittedDate(submittedDates[0].toISOString())
    }

    const fallbackSubmittedAt = submittedAssessment?.submittedAt ?? assessmentMeta?.submittedAt
    return isSubmitted ? formatSubmittedDate(fallbackSubmittedAt) : ''
  })()

  function questionsForPdf(questions = []) {
    return questions
      .slice()
      .sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0))
      .map((question) => {
        const code = questionCodeOf(question)
        const answer = answers?.[code] ?? {}
        return {
          text: question?.text ?? code,
          score: answer?.answered === true ? answer.score : null,
          answeredAt: answer?.answeredAt,
        }
      })
  }

  function clientPdfDomains() {
    if (framework === 'cmmi') {
      const grouped = new Map()
      for (const seg of frameworkSegments) {
        const lines = cmmiDomainLines(seg)
        const domainTitle = lines?.domainLine ?? 'CMMI'
        const subdomainName = lines?.subdomainLine ?? domainTitle
        if (!grouped.has(domainTitle)) {
          grouped.set(domainTitle, {
            title: domainTitle,
            score: null,
            questions: [],
            subdomains: [],
          })
        }
        grouped.get(domainTitle).subdomains.push({
          name: subdomainName,
          questions: questionsForPdf(seg.questions),
        })
      }
      return [...grouped.values()]
    }

    return frameworkSegments.map((seg) => ({
      title: domainTitle(seg),
      score: segmentAverage(seg),
      questions: questionsForPdf(seg.questions),
      subdomains: [],
    }))
  }

  function onExportPdf() {
    if (!isStaff) return
    const frameworkLabel = selectedFrameworkOption?.label ?? frameworkLabelFromKey(framework)
    exportAssessmentPdf({
      clientName: auth.subject ?? 'Client',
      year: assessmentMeta?.year,
      version: assessmentMeta?.versionNumber ?? assessmentMeta?.version,
      status: 'SUBMITTED',
      submittedAt: submittedAssessment?.submittedAt ?? assessmentMeta?.submittedAt,
      frameworks: [
        {
          label: frameworkLabel,
          globalScore: submittedAssessment?.globalScore ?? assessmentMeta?.globalScore ?? frameworkProgress.avg,
          overallAverageScore: averageFrameworkScore,
          domains: clientPdfDomains(),
        },
      ],
    })
  }

  return (
    <div className="container">
      <div className="page">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">{staffMode ? 'Staff assessment edit' : 'Assessment'}</h1>
            {staffMode ? (
              <div className="staffEditIdentityBanner" aria-label="Edited client assessment">
                <div className="staffEditClientName">
                  <span aria-hidden="true">👤</span>
                  <strong>{staffClientName}</strong>
                </div>
                {staffClientEmail ? (
                  <div className="staffEditClientEmail">
                    <span aria-hidden="true">✉️</span>
                    <span>{staffClientEmail}</span>
                  </div>
                ) : null}
                <div className="staffEditMetaBadges">
                  <span className="staffEditMetaBadge">
                    <span aria-hidden="true">📅</span>
                    {staffAssessmentYear}
                  </span>
                  <span className="staffEditMetaBadge">
                    <FileText size={14} strokeWidth={2.2} aria-hidden="true" />
                    Version {staffAssessmentVersion}
                  </span>
                  <span className={`staffEditStatusBadge staffEditStatus${isSubmitted ? 'Submitted' : 'CurrentAssessment'}`}>
                    {isSubmitted ? (
                      <CircleCheck size={14} strokeWidth={2.2} aria-hidden="true" />
                    ) : (
                      <Clock size={14} strokeWidth={2.2} aria-hidden="true" />
                    )}{' '}
                    {currentStatus}
                  </span>
                </div>
              </div>
            ) : null}
            <p className="pageSub">
              {staffMode
                ? 'Edit the selected client assessment with the same questionnaire view.'
                : 'Pick a framework, then select a domain in the left dashboard to answer its questions.'}
            </p>
          </div>
          <div className="metaPillStack">
            {staffMode && isStaff ? (
              <button
                type="button"
                className="btn btnGhost btnSm btnWithIcon"
                onClick={() => navigate(homePathForRole(role))}
              >
                <BtnIcon icon={ArrowLeft} />
                Back to staff dashboard
              </button>
            ) : null}
            <button
              type="button"
              className={`metaPill${staffMode ? '' : ' metaPillClickable'}`}
              style={{ border: 0 }}
              onClick={() => {
                if (!staffMode) setClientVersionsOpen((value) => !value)
              }}
              aria-expanded={staffMode ? undefined : clientVersionsOpen}
            >
              <span>{currentStatus}</span>
              <strong>{assessmentMeta?.year ?? '—'}</strong>
              {!staffMode ? (
                <span className="metaPillMenuIcon" aria-hidden="true">
                  ☰
                </span>
              ) : null}
            </button>
            {!staffMode && latestSubmissionDate ? (
              <div className="metaPillSubmissionDate">Latest submission: {latestSubmissionDate}</div>
            ) : null}
            {!staffMode && clientVersionsOpen ? (
              <div className="clientVersionMenu sectionCard">
                <div className="sectionHeader" style={{ marginBottom: 8 }}>
                  <div>
                    <h2 className="sectionTitle" style={{ fontSize: 16 }}>
                      Assessment versions
                    </h2>
                    <p className="muted" style={{ margin: 0 }}>
                      Your own assessment history.
                    </p>
                  </div>
                </div>
                {clientVersionsLoading ? <p className="muted">Loading versions...</p> : null}
                {clientVersionsError ? <p className="muted">{clientVersionsError}</p> : null}
                {!clientVersionsLoading && clientVersions.length === 0 && !clientVersionsError ? (
                  <p className="muted">{EMPTY_ASSESSMENT_VERSIONS_MESSAGE}</p>
                ) : null}
                {clientVersions.length > 0 ? (
                  <div className="clientVersionList">
                    {clientVersions.map((row) => (
                      <button
                        key={String(row.id)}
                        type="button"
                        className={`clientVersionRow${String(row.id) === String(selectedClientVersionId) ? ' clientVersionRowActive' : ''}`}
                        onClick={() => onSelectClientVersion(row)}
                      >
                        <span>
                          <strong>
                            Version {row.versionNumber}
                            {row.versionComment ? ` — ${row.versionComment}` : ''}
                          </strong>{' '}
                          {row.isLatest ? <span className="verBadge verBadgeLatest">Latest</span> : null}
                        </span>
                        <span className="muted">
                          {versionStatusLabel(row.status)} — {versionSubmittedText(row)}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>

        {error ? <div className={`alert ${permissionDenied ? 'alertInfo' : 'alertError'}`}>{error}</div> : null}
        {loading ? <p>Loading…</p> : null}

        {!loading && questionnaire ? (
          <div className="assessmentLayout">
            <aside className="assessmentSidebar">
              <div className="sbBrand">
                <div className="sbLogo" aria-hidden="true" />
                <div className="sbTitle">Assessment</div>
              </div>

              <div className="sbSectionLabel">Framework</div>
              <select
                className="sbSelect"
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                disabled={frameworkOptions.length <= 1}
              >
                {frameworkOptions.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label}
                  </option>
                ))}
              </select>

              <div className="sbMetrics">
                <div className="sbMetric sbMetricWide">
                  <span className="sbMetricLabel">Progress</span>
                  <strong>
                    {frameworkProgress.answered}/{frameworkProgress.total}
                  </strong>
                </div>
                <div className="sbMetric">
                  <span className="sbMetricLabel">Overall Score</span>
                  <strong>{frameworkProgress.avg ?? '—'}</strong>
                </div>
                <div className="sbMetric">
                  <span className="sbMetricLabel">Overall Average Score</span>
                  <strong>{averageFrameworkScore ?? assessmentMeta?.globalAverageScore ?? '—'}</strong>
                </div>
              </div>

              <div className="sbSectionLabel">Domains</div>
              <div className="domainList">
                {frameworkSegments.map((seg) => {
                  const active = seg.code === activeSegmentCode
                  const { done, total } = segmentProgress(seg)
                  const cmmiLines = cmmiDomainLines(seg)
                  return (
                    <button
                      key={seg.code}
                      type="button"
                      className={active ? 'domainBtn domainBtnActive' : 'domainBtn'}
                      onClick={() => setActiveSegmentCode(seg.code)}
                    >
                      <span className="domainDot" aria-hidden="true" />
                      <span className="domainText">
                        {cmmiLines ? (
                          <>
                            {cmmiLines.domainLine ? (
                              <span className="domainGroupLabel">{cmmiLines.domainLine}</span>
                            ) : null}
                            <span className="domainName">{cmmiLines.subdomainLine}</span>
                          </>
                        ) : (
                          <span className="domainName">{domainTitle(seg)}</span>
                        )}
                        <span className="domainMeta">
                          {done}/{total} · score {segmentAverage(seg) ?? '—'} · domain avg {segmentDisplayAverage(seg) ?? '—'}
                        </span>
                      </span>
                    </button>
                  )
                })}
              </div>

              <div className="sbSectionLabel">Scores</div>
              <div className="sbScoreboard">
                {domainScoreboard.rows.map((row) => (
                  <div key={row.code} className="sbScoreRow">
                    <div className="sbScoreTitle" title={row.title}>
                      {row.title}
                    </div>
                    <div className="sbScoreValue">
                      <>
                        <div>
                          Official score: <strong>{row.avg ?? '—'}</strong>
                        </div>
                        <div className="sbScoreIncomplete">
                          Domain average: <strong>{row.averageScore ?? '—'}</strong>
                        </div>
                        {row.label ? <span className="sbScoreHint"> ({row.label})</span> : null}
                        {!row.complete ? <div className="sbScoreIncomplete">Incomplete</div> : null}
                        <div className="sbScoreIncomplete">
                          {row.answeredQuestions}/{row.totalQuestions}
                        </div>
                      </>
                    </div>
                  </div>
                ))}

                <div className="sbScoreTotal">
                  <div className="sbScoreTotalLabel">Total</div>
                  <div className="sbScoreTotalValue">
                    <>
                      <strong>{domainScoreboard.totalAvg ?? '—'}</strong>
                      {domainScoreboard.totalLabel ? (
                        <span className="sbScoreHint"> ({domainScoreboard.totalLabel})</span>
                      ) : null}
                      {!isComplete ? <div className="sbScoreIncomplete">Incomplete</div> : null}
                    </>
                  </div>
                  <div className="sbScoreFootnote">Total = weighted average of domain scores.</div>
                </div>
              </div>

              <div className="sbStatsActions">
                {canExportPdf ? (
                  <button
                    type="button"
                    className="sbViewStatsBtn"
                    onClick={onExportPdf}
                  >
                    Export Assessment Report
                  </button>
                ) : null}
                <button
                  type="button"
                  className="sbViewStatsBtn"
                  onClick={() => setShowStatistics((v) => !v)}
                  aria-expanded={showStatistics}
                >
                  {showStatistics ? 'Hide statistics' : 'View statistics'}
                </button>
              </div>

              <div className="sbFooter">
                <div className="sbSectionLabel">Analysis</div>
                <div className="sbMuted">
                  {staffMode ? 'Staff changes are saved as current assessment answers.' : 'Results appear after you submit'}
                </div>
              </div>
            </aside>

            <section className="assessmentMain">
              {showStatistics ? (
                <div className="statsGrid" ref={statisticsSectionRef} style={{ scrollMarginTop: 88 }}>
                  {frameworkSegments.length > 0 ? (
                    <div className="chartCard radarChartCard">
                      <FrameworkRadarChart
                        framework={framework}
                        rows={domainAnalysisItems}
                        summaryValue={radarSummary.value}
                        summaryBandLabel={radarSummary.bandLabel}
                      />
                    </div>
                  ) : null}

                  {activeSegment && segmentQuestionPoints.length > 0 ? (
                    <div className="chartCard radarChartCard">
                      <SegmentRadarChart
                        title={
                          cmmiDomainLines(activeSegment)?.subdomainLine ??
                          domainTitle(activeSegment)
                        }
                        points={segmentQuestionPoints}
                      />
                    </div>
                  ) : null}
                </div>
              ) : null}

              {activeSegment ? (
                <>
                  <div className="mainHead">
                    <div>
                      <div className="mainKicker">
                        {selectedFrameworkOption?.label ?? frameworkLabelFromKey(framework)}
                      </div>
                      {(() => {
                        const lines = cmmiDomainLines(activeSegment)
                        if (lines) {
                          return (
                            <>
                              {lines.domainLine ? (
                                <div className="cmmiDomainHeading">{lines.domainLine}</div>
                              ) : null}
                              <h2 className="mainTitle">{lines.subdomainLine}</h2>
                            </>
                          )
                        }
                        return <h2 className="mainTitle">{domainTitle(activeSegment)}</h2>
                      })()}
                      <p className="mainSub">
                        Segment code: <code>{activeSegment.code}</code>
                      </p>
                    </div>
                    <div className="badge">
                      {(activeSegment.questions ?? []).length} question(s)
                    </div>
                  </div>

                  <div className="scorePanel">
                    <div className="scorePanelTitle">Scoring</div>
                    <div className="scorePanelGrid">
                      <div className="scoreStat">
                        <div className="scoreStatLabel">Domain score (minimum)</div>
                        <div className="scoreStatValue">
                          {activeSegmentScoring.avg ?? '—'}{' '}
                          {activeSegmentScoring.label ? (
                            <span className="scoreStatHint">({activeSegmentScoring.label})</span>
                          ) : null}
                        </div>
                        <div className="scoreStatHint">
                          Domain score is the <strong>minimum</strong> of scored questions in this domain.
                        </div>
                      </div>
                      <div className="scoreStat">
                        <div className="scoreStatLabel">Scale</div>
                        <div className="scoreStatHint">
                          {framework === 'ndi' ? (
                            <>
                              NDI uses <strong>0–5</strong>. CMMI uses <strong>1–5</strong>.
                            </>
                          ) : (
                            <>
                              CMMI uses <strong>1–5</strong>. NDI uses <strong>0–5</strong>.
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="legend">
                      {framework === 'ndi' ? (
                        <>
                          <div className="legendTitle">NDI labels</div>
                          <ul className="legendList">
                            <li>
                              <strong>0</strong> — Absence of capabilities
                            </li>
                            <li>
                              <strong>1</strong> — Establishing
                            </li>
                            <li>
                              <strong>2</strong> — Defined
                            </li>
                            <li>
                              <strong>3</strong> — Activated
                            </li>
                            <li>
                              <strong>4</strong> — Managed
                            </li>
                            <li>
                              <strong>5</strong> — Pioneer
                            </li>
                          </ul>
                        </>
                      ) : (
                        <>
                          <div className="legendTitle">CMMI labels</div>
                          <ul className="legendList">
                            <li>
                              <strong>1</strong> — Performed
                            </li>
                            <li>
                              <strong>2</strong> — Managed
                            </li>
                            <li>
                              <strong>3</strong> — Defined
                            </li>
                            <li>
                              <strong>4</strong> — Measured
                            </li>
                            <li>
                              <strong>5</strong> — Optimized
                            </li>
                          </ul>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="qList">
                    {readOnlyVersion ? (
                      <div className="alert alertInfo">
                        You are viewing an old assessment version in read-only mode.
                        {selectedClientVersion ? ` Version ${selectedClientVersion.versionNumber}.` : ''}
                      </div>
                    ) : null}
                    {(activeSegment.questions ?? [])
                      .slice()
                      .sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0))
                      .map((q) => {
                        const opts = scoreOptionsForCode(q.code)
                        const answered = questionAnswered(q)
                        const v = answered ? answers?.[q.code]?.score : null
                        const ev = evidences?.[q.code] ?? null
                        const evidenceItems = [
                          ...(ev?.items ?? []),
                          ...(ev?.pendingFiles ?? []).map((file) => ({ id: `pending-${file.name}`, fileName: `${file.name} (pending)` })),
                        ]
                        const ratingLabel =
                          ev?.staffRating
                            ? { LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High' }[String(ev.staffRating).toUpperCase()] ??
                              String(ev.staffRating)
                            : ''
                        return (
                          <article key={q.code} className="qCard qCardLong">
                            <div className="qCardTop">
                              <div className="qCardId">{q.code}</div>
                              <div className="qCardText">{q.text}</div>
                              {!answered ? <div className="tinyNote muted">Not answered</div> : null}
                              <div className="qCardActionsRow">
                                {!readOnlyVersion ? (
                                <label className="uploadEvidenceBtn" title="Upload evidence">
                                  <input
                                    type="file"
                                    multiple
                                    className="evidenceInput"
                                    onChange={async (e) => {
                                      const files = Array.from(e.target.files ?? [])
                                      e.target.value = ''
                                      if (files.length === 0) return
                                      try {
                                        await uploadEvidences(q.code, files)
                                      } catch (err) {
                                        setError(err?.message ?? 'Evidence upload failed')
                                      }
                                    }}
                                  />
                                  <span className="uploadEvidenceIcon" aria-hidden="true">
                                    <Upload size={16} strokeWidth={2.2} />
                                  </span>
                                  <span>Upload Evidence</span>
                                </label>
                                ) : null}
                              </div>
                            </div>

                            <div className="qCardGrid">
                              <label className="field">
                                <span className="label">Score</span>
                                <select
                                  className="selectDark"
                                  value={v === null || v === undefined ? '' : String(v)}
                                  disabled={readOnlyVersion}
                                  onChange={(e) => {
                                    const raw = e.target.value
                                    if (raw === '') return
                                    setScore(q.code, Number(raw))
                                  }}
                                >
                                  <option value="">Choose a score…</option>
                                  {opts.map((o) => (
                                    <option key={o.value} value={String(o.value)}>
                                      {o.label}
                                    </option>
                                  ))}
                                </select>

                                {evidenceItems.length > 0 ? (
                                  <div className="evidenceMeta">
                                    <EvidenceFilesPanel
                                      answerId={q.code}
                                      items={evidenceItems.map((item) => ({
                                        id: item.id ?? item.evidenceId,
                                        fileName: item.fileName ?? '',
                                        sizeBytes: item.sizeBytes ?? item.size ?? item.fileSize ?? null,
                                      }))}
                                      canDelete={canDeleteEvidence}
                                      deletingId={deletingId}
                                      onRequestDelete={(item) =>
                                        setPendingDelete({
                                          id: item.id,
                                          fileName: item.fileName,
                                          questionCode: q.code,
                                        })
                                      }
                                      emptyLabel="No evidence"
                                    />
                                    {ev.staffRating ? (
                                      <span className={`evidenceRating evidenceRating${String(ev.staffRating).toUpperCase()}`}>
                                        {ratingLabel}
                                      </span>
                                    ) : null}
                                    <button
                                      type="button"
                                      className="btn btnGhost btnSm"
                                      disabled={(ev?.items?.length ?? 0) === 0}
                                      onClick={async () => {
                                        try {
                                          await downloadAllEvidencesForQuestion(q.code)
                                        } catch (err) {
                                          setError(err?.message ?? 'Download failed')
                                        }
                                      }}
                                    >
                                      Download all
                                    </button>
                                  </div>
                                ) : (
                                  <EvidenceFilesPanel answerId={q.code} items={[]} emptyLabel="No evidence" />
                                )}
                              </label>

                              <label className="field">
                                <span className="label">Comment (label + details)</span>
                                <textarea
                                  className="textareaDark"
                                  value={answers?.[q.code]?.comment ?? ''}
                                  disabled={readOnlyVersion}
                                  onChange={(e) => setComment(q.code, e.target.value)}
                                  placeholder="The label is filled automatically when you pick a score — add context here."
                                  rows={3}
                                />
                              </label>
                            </div>
                          </article>
                        )
                      })}
                  </div>

                  <div className="footerBar">
                    <div className="footerLeft">
                      {readOnlyVersion ? (
                        <span className="muted">Read-only version: old versions cannot be modified.</span>
                      ) : staffMode ? (
                        <span className="muted">{staffFooterMessage}</span>
                      ) : (
                        <span className="muted">{clientFooterMessage}</span>
                      )}
                    </div>
                    {readOnlyVersion ? null : (
                      <div className="footerActions">
                        {canShowVersionComment ? (
                          <label className="versionCommentField">
                            <span className="label">Version comment (optional)</span>
                            <textarea
                              className="textareaDark"
                              value={versionComment}
                              onChange={(e) => setVersionComment(e.target.value)}
                              placeholder="Describe what changed in this version..."
                              rows={2}
                              maxLength={1000}
                              disabled={submitting}
                            />
                          </label>
                        ) : null}
                        <button
                          type="button"
                          className="btn btnPrimary"
                          disabled={staffMode ? !staffCanSubmit || submitting : !clientSubmitAllowed || submitting}
                          onClick={onSubmit}
                        >
                          {!staffMode && isSubmitted && !clientPendingVersionSubmit ? 'Submitted' : submitting ? 'Submitting…' : 'Submit'}
                        </button>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <p className="muted">No domains available for this framework.</p>
              )}

              {submittedAssessment ? (
                <section className="sectionCard" style={{ marginTop: 16 }}>
                  <div className="sectionHeader">
                    <div>
                      <h2 className="sectionTitle">Result</h2>
                      <p className="sectionHint">
                        Overall Score: <strong>{submittedAssessment.globalScore}</strong> —{' '}
                        {submittedAssessment.globalMaturityLabel}
                        {submittedAssessment.globalAverageScore != null ? (
                          <>
                            {' '}
                            · Overall Average Score: <strong>{submittedAssessment.globalAverageScore}</strong>
                          </>
                        ) : null}
                      </p>
                    </div>
                    <div className="badge">{submittedAssessment.status}</div>
                  </div>
                </section>
              ) : null}
            </section>
          </div>
        ) : null}
      </div>
      <EvidenceDeleteConfirmModal
        open={Boolean(pendingDelete)}
        fileName={pendingDelete?.fileName || `Evidence ${pendingDelete?.id ?? ''}`}
        deleting={deletingId != null}
        onCancel={() => {
          if (deletingId != null) return
          setPendingDelete(null)
        }}
        onConfirm={confirmDeleteEvidence}
      />
    </div>
  )
}
