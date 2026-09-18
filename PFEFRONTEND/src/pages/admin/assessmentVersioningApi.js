/**
 * Admin assessment versioning — API paths and response normalization.
 * Adjust paths here if your Spring controller uses different URLs.
 */
export const assessmentVersionsListPath = (clientId) =>
  `/api/admin/clients/${clientId}/assessment-versions`

export const assessmentVersionDetailPath = (clientId, versionId) =>
  `/api/admin/clients/${clientId}/assessment-versions/${versionId}`

function normalizeFrameworkStatusList(value) {
  const rows = Array.isArray(value) ? value : []
  return rows.map((item) => ({
    frameworkCode: item.frameworkCode ?? item.code ?? item.framework ?? '—',
    frameworkStatus: item.frameworkStatus ?? item.status ?? '—',
    frameworkScore: item.frameworkScore ?? item.score ?? null,
    frameworkAverageScore: item.frameworkAverageScore ?? item.framework_average_score ?? null,
    answeredQuestions: item.answeredQuestions ?? 0,
    totalQuestions: item.totalQuestions ?? 0,
    isComplete: item.isComplete ?? item.complete ?? false,
    lastSubmissionDate:
      item.lastSubmissionDate ??
      item.lastSubmittedAt ??
      item.frameworkSubmittedAt ??
      item.submittedAt ??
      item.submitted_at ??
      null,
    submittedAt:
      item.submittedAt ??
      item.submitted_at ??
      item.lastSubmissionDate ??
      item.lastSubmittedAt ??
      item.frameworkSubmittedAt ??
      null,
  }))
}

function formatFrameworkStatusList(rows) {
  return rows.length
    ? rows
        .map((item) => `${item.frameworkCode}: ${item.frameworkStatus} (${item.answeredQuestions}/${item.totalQuestions})`)
        .join(' + ')
    : '—'
}

export function normalizeVersionRow(v, index) {
  const id = v.id ?? v.versionId ?? v.assessmentVersionId ?? v.assessmentId
  const versionNumber = v.versionNumber ?? v.version ?? v.sequence ?? index + 1
  const createdAt = v.createdAt ?? v.versionCreatedAt ?? v.created_at ?? null
  const frameworkStatus = normalizeFrameworkStatusList(v.frameworkStatus ?? v.frameworkDetails)
  const framework = frameworkStatus.length
    ? formatFrameworkStatusList(frameworkStatus)
    : v.framework ?? v.frameworkName ?? v.frameworkCode ?? v.frameworkKey ?? '—'
  const globalScore = v.globalScore ?? v.global_score ?? v.score ?? null
  const globalAverageScore = v.globalAverageScore ?? v.global_average_score ?? null
  const status = v.globalStatus ?? v.status ?? v.versionStatus ?? '—'
  const isLatestFlag = Boolean(v.isLatest ?? v.latest)
  const versionComment = v.versionComment ?? v.submissionComment ?? v.comment ?? v.version_comment ?? null
  return { raw: v, id, versionNumber, createdAt, framework, frameworkStatus, globalScore, globalAverageScore, status, isLatestFlag, versionComment }
}

/** After mapping rows, set exactly one `isLatest` for UI badges. */
export function markLatestVersion(rows) {
  const list = Array.isArray(rows) ? [...rows] : []
  const explicitIndices = list.map((r, i) => (r.isLatestFlag ? i : -1)).filter((i) => i >= 0)
  if (explicitIndices.length > 0) {
    const keep = explicitIndices[0]
    return list.map((r, i) => ({ ...r, isLatest: i === keep }))
  }
  if (list.length === 0) return list
  let best = 0
  for (let i = 1; i < list.length; i++) {
    const a = Number(list[i].versionNumber)
    const b = Number(list[best].versionNumber)
    if (!Number.isNaN(a) && !Number.isNaN(b) && a > b) best = i
  }
  return list.map((r, i) => ({ ...r, isLatest: i === best }))
}

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null)
}

function asArray(value) {
  return Array.isArray(value) ? value : []
}

function toFiniteNumber(value) {
  if (value === undefined || value === null || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function normalizeAnsweredFlag(value) {
  if (value === true || value === false) return value
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (normalized === 'true') return true
    if (normalized === 'false') return false
  }
  return undefined
}

function roundScore(value) {
  const n = toFiniteNumber(value)
  return n === null ? null : Math.round(n * 100) / 100
}

function normalizeEvidenceItem(raw) {
  const id = firstDefined(raw?.id, raw?.evidenceId, raw?.evidence_id)
  if (!id) return null
  return {
    id,
    evidenceId: id,
    fileName: firstDefined(raw?.fileName, raw?.originalFileName, raw?.evidenceFileName, raw?.name, ''),
    fileUrl: firstDefined(raw?.fileUrl, raw?.downloadUrl, raw?.url, raw?.evidenceUrl, ''),
    downloadUrl: firstDefined(raw?.downloadUrl, raw?.fileUrl, raw?.url, raw?.evidenceUrl, ''),
    uploadedAt: firstDefined(raw?.uploadedAt, raw?.createdAt, raw?.created_at, ''),
  }
}

function evidencesFromAnswer(q) {
  const items = asArray(q?.evidences).map(normalizeEvidenceItem).filter(Boolean)
  if (items.length > 0) return items
  const legacy = normalizeEvidenceItem({
    id: firstDefined(q?.evidenceId, q?.evidence?.id),
    fileName: firstDefined(q?.evidenceFileName, q?.evidence?.fileName, q?.fileName),
    downloadUrl: firstDefined(q?.evidenceUrl, q?.evidence_url, q?.evidence?.url),
    uploadedAt: firstDefined(q?.evidence?.uploadedAt, q?.evidence?.createdAt),
  })
  return legacy ? [legacy] : []
}

function frameworkKeyFromValue(value) {
  const raw = String(value ?? '').trim().toLowerCase()
  if (!raw) return ''
  const normalized = raw.replaceAll(/[\s-]+/g, '_')
  if (normalized === 'ndi') return 'ndi'
  if (normalized === 'cmmi' || normalized === 'cmmi_dmm') return 'cmmi'
  return normalized
}

function frameworkKeyFromSegment(seg) {
  const direct = frameworkKeyFromValue(
    seg?.frameworkKey ?? seg?.frameworkCode ?? seg?.framework ?? seg?.frameworkName,
  )
  if (direct) return direct

  const code = String(seg?.segmentCode ?? seg?.code ?? seg?.domainCode ?? '')
  const title = String(seg?.segmentTitle ?? seg?.title ?? seg?.name ?? seg?.domainName ?? '')
  if (code.startsWith('cmmi_') || title.startsWith('CMMI DMM ·')) return 'cmmi'
  if (code.startsWith('ndi_')) return 'ndi'
  return ''
}

function frameworkLabelFromKey(key) {
  if (key === 'ndi') return 'NDI'
  if (key === 'cmmi') return 'CMMI'
  return String(key ?? '').replaceAll('_', ' ').toUpperCase()
}

const NDI_DOMAIN_TITLES = {
  ndi_dg: 'Data Governance',
  ndi_do: 'Data Operations',
  ndi_mcm: 'Metadata Management',
  ndi_dq: 'Data Quality',
  ndi_da: 'Data Architecture',
  ndi_dam: 'Data Architecture Management',
  ndi_dc: 'Data Classification',
  ndi_dcm: 'Data Change Management',
  ndi_dm: 'Data Management',
  ndi_dsi: 'Data Sharing and Integration',
  ndi_dvr: 'Data Value Realization',
  ndi_foi: 'Freedom of Information',
  ndi_bia: 'Business Intelligence and Analytics',
  ndi_od: 'Open Data',
  ndi_pdp: 'Personal Data Protection',
  ndi_rmd: 'Reference and Master Data',
}

const NDI_DOMAIN_CODES_BY_ABBREVIATION = Object.fromEntries(
  Object.keys(NDI_DOMAIN_TITLES).map((code) => [code.replace(/^ndi_/u, '').toUpperCase(), code]),
)

const UNTITLED_DOMAIN_LABEL = 'Domain'

const CMMI_PARENT_DOMAIN_TITLES = {
  1: 'Data Management Strategy & Business Case',
  2: 'Data Governance',
  3: 'Data Quality',
  4: 'Data Operations & Lifecycle',
  5: 'Data Architecture & Technology',
  6: 'Process & Measurement',
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

function maturityLabelForScore(frameworkKey, score) {
  const rounded = Math.max(0, Math.min(5, Math.round(Number(score))))
  if (frameworkKey === 'ndi') return ndiLabel(rounded)
  if (frameworkKey === 'cmmi') return rounded === 0 ? '' : cmmiLabel(rounded)
  return ''
}

function normalizeAnswer(q, fallbackCode = '') {
  const question = q?.question && typeof q.question === 'object' ? q.question : null
  const domain = q?.domain && typeof q.domain === 'object' ? q.domain : null
  const questionCode = firstDefined(q?.questionCode, q?.code, q?.question_code, question?.code, fallbackCode)
  const evidences = evidencesFromAnswer(q)
  const firstEvidence = evidences[0] ?? null
  return {
    questionCode,
    questionText: firstDefined(q?.questionText, q?.text, q?.label, question?.text, ''),
    score: firstDefined(q?.score, q?.answerScore, q?.value),
    domainCode: firstDefined(
      q?.domainCode,
      q?.domain_code,
      q?.segmentCode,
      q?.segment_code,
      question?.domainCode,
      question?.domain_code,
      domain?.code,
      domain?.domainCode,
    ),
    domainTitle: firstDefined(
      q?.domainTitle,
      q?.domainName,
      q?.domain_name,
      q?.segmentTitle,
      q?.segment_title,
      question?.domainTitle,
      question?.domainName,
      domain?.title,
      domain?.name,
      domain?.domainName,
    ),
    evidenceId: firstDefined(firstEvidence?.id, q?.evidenceId, q?.evidence?.id),
    evidenceFileName: firstDefined(firstEvidence?.fileName, q?.evidenceFileName, q?.evidence?.fileName, q?.fileName),
    evidences,
    evidenceStaffRating: firstDefined(q?.evidenceStaffRating, q?.staffRating, q?.evidence?.staffRating),
    evidenceStaffComment: firstDefined(q?.evidenceStaffComment, q?.staffComment, q?.evidence?.staffComment, ''),
    answeredAt: firstDefined(q?.answeredAt, q?.answered_at, q?.submittedAt, q?.submitted_at, q?.updatedAt, q?.updated_at),
    answered: normalizeAnsweredFlag(firstDefined(q?.answered, q?.isAnswered, q?.answered_flag)),
    selectedScore: firstDefined(q?.selectedScore, q?.selected_score),
    comment: firstDefined(q?.comment, q?.note, q?.answerComment, q?.answer_comment, ''),
  }
}

function collectSegmentAnswers(segment) {
  return [
    ...(segment.answers ?? []),
    ...(segment.subDomains ?? []).flatMap((sub) => sub.answers ?? []),
  ]
}

function clientLikeSegmentScore(segment, directScore) {
  const answers = collectSegmentAnswers(segment)
  if (!answers.length) return directScore

  const values = answers
    .map((answer) => toFiniteNumber(answer.score))
    .filter((value) => value !== null)

  if (values.length !== answers.length) return 0
  if (values.length === 0) return directScore

  return roundScore(Math.min(...values))
}

function displayAverageScore(segment) {
  const values = collectSegmentAnswers(segment)
    .map((answer) => toFiniteNumber(answer.score))
    .filter((value) => value !== null)

  if (!values.length) return null
  return roundScore(values.reduce((sum, value) => sum + value, 0) / values.length)
}

function domainCodeFromQuestionCode(questionCode) {
  const code = String(questionCode ?? '').trim()
  if (!code) return ''

  const parts = code.split('_').filter(Boolean)
  if (parts[0] === 'ndi' && parts.length >= 3) return parts.slice(0, 2).join('_')
  if (parts[0] === 'cmmi' && parts.length >= 4) return parts.slice(0, 3).join('_')

  const withoutTrailingNumber = code.replace(/_[a-z]*\d+[a-z]*$/i, '')
  return withoutTrailingNumber !== code ? withoutTrailingNumber : ''
}

function humanizeDomainCode(code) {
  const normalized = String(code ?? '').trim()
  if (!normalized) return UNTITLED_DOMAIN_LABEL
  if (NDI_DOMAIN_TITLES[normalized]) return NDI_DOMAIN_TITLES[normalized]
  const cmmiParentTitle = cmmiParentTitleFromCode(normalized)
  if (cmmiParentTitle) return cmmiParentTitle

  const parts = normalized
    .replace(/^(?:ndi|cmmi)[_\s-]*/iu, '')
    .split(/[_\s-]+/u)
    .filter(Boolean)

  const readable = parts
    .map((part) => {
      if (/^\d+$/u.test(part)) return part
      return `${part[0]?.toUpperCase() ?? ''}${part.slice(1).toLowerCase()}`
    })
    .join(' ')

  return readable ? `Domain ${readable}` : UNTITLED_DOMAIN_LABEL
}

function cmmiParentTitleFromCode(code) {
  const normalized = String(code ?? '').trim().toLowerCase()
  const match = normalized.match(/^cmmi_(\d+)(?:_\d+)?$/u) ?? normalized.match(/^(\d+)(?:[\s._-]+\d+)?$/u)
  if (!match) return ''
  return CMMI_PARENT_DOMAIN_TITLES[match[1]] ?? ''
}

function cmmiCodeParts(code) {
  const normalized = String(code ?? '').trim().toLowerCase()
  const match = normalized.match(/^cmmi_(\d+)_(\d+)$/u)
  if (!match) return null
  return { major: match[1], minor: match[2], subCode: `${match[1]}.${match[2]}` }
}

function cleanDomainTitle(title) {
  return String(title ?? '').replace(/^CMMI DMM ·\s*/u, '').trim()
}

function isCodeLikeTitle(title) {
  const value = String(title ?? '').trim()
  if (!value) return true
  if (/^(?:ndi|cmmi)[_\s-]/iu.test(value)) return true
  if (/^\d+(?:[\s._-]+\d+)+$/u.test(value)) return true
  return false
}

function normalizeDomainCode(value) {
  const raw = String(value ?? '').trim()
  if (!raw) return ''

  const normalized = raw.toLowerCase().replaceAll(/[\s-]+/g, '_')
  if (NDI_DOMAIN_TITLES[normalized]) return normalized

  const abbreviation = raw.toUpperCase().replaceAll(/[\s-]+/g, '_')
  return NDI_DOMAIN_CODES_BY_ABBREVIATION[abbreviation] ?? raw
}

function normalizeDomainTitle(code, rawTitle) {
  const normalizedCode = normalizeDomainCode(code)
  const mappedTitle = NDI_DOMAIN_TITLES[normalizedCode]
  if (mappedTitle) return mappedTitle

  const title = cleanDomainTitle(rawTitle)
  if (!title) return humanizeDomainCode(normalizedCode)
  if (isCodeLikeTitle(title)) return humanizeDomainCode(normalizedCode)

  const codeSuffix = normalizedCode.split('_').filter(Boolean).at(-1)?.toUpperCase() ?? ''
  const titleLooksAbbreviated = !title.includes(' ') && title.length <= 4
  if (titleLooksAbbreviated && title.toUpperCase() === codeSuffix) {
    return humanizeDomainCode(normalizedCode)
  }

  return title
}

function normalizeSubDomainName(sub, fallbackIndex) {
  const name = cleanDomainTitle(firstDefined(sub?.name, sub?.title, sub?.subDomainName, sub?.sub_domain_name, ''))
  if (name && !isCodeLikeTitle(name)) return name

  const code = firstDefined(sub?.code, sub?.subDomainCode, sub?.sub_domain_code, '')
  const parentTitle = cmmiParentTitleFromCode(code)
  if (parentTitle) return parentTitle

  return `Sub-domain ${fallbackIndex + 1}`
}

function cmmiSubDomainName(segment) {
  const parts = cmmiCodeParts(segment?.segmentCode)
  const title = cleanDomainTitle(segment?.segmentTitle)
  const titleMatch = title.match(/^\d+\.\d+\s+(.+)$/u)
  if (titleMatch?.[1]) return titleMatch[1].trim()
  const parentTitle = parts ? CMMI_PARENT_DOMAIN_TITLES[parts.major] : ''
  if (title && title !== parentTitle && !isCodeLikeTitle(title) && !title.startsWith('Domain ')) return title
  return parts ? `Sub-domain ${parts.subCode}` : 'Sub-domain'
}

function titleFromQuestionText(questionText, code) {
  const text = String(questionText ?? '').replaceAll(/\s+/g, ' ').trim()
  const abbreviation = normalizeDomainCode(code).replace(/^ndi_/u, '').toUpperCase()
  if (!text || !abbreviation) return ''

  const escapedAbbr = abbreviation.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const acronymMatch = text.match(
    new RegExp(
      `((?:Data|Business|Foundation|Reference|Metadata|Information|Change)[A-Za-z]*(?:[\\s&/-]+[A-Z]?[A-Za-z]+){0,8})\\s*\\(\\s*${escapedAbbr}\\s*\\)`,
      'i',
    ),
  )
  if (!acronymMatch?.[1]) return ''

  return acronymMatch[1]
    .replace(/^(?:Has the entity |the entity |an? )/iu, '')
    .replace(/\s+(?:plan|capabilities|practices)\b.*$/iu, '')
    .trim()
}

function titleFromAnswers(answers, code) {
  for (const answer of answers ?? []) {
    const title = titleFromQuestionText(answer?.questionText, code)
    if (title && !isCodeLikeTitle(title) && !isAbbreviatedTitle(title, code)) return title
  }
  return ''
}

function isAbbreviatedTitle(title, code) {
  const value = String(title ?? '').trim()
  if (!value) return true
  if (value === UNTITLED_DOMAIN_LABEL) return true
  if (value.startsWith('Domain ')) return true
  const suffix = normalizeDomainCode(code).split('_').filter(Boolean).at(-1)?.toUpperCase() ?? ''
  return !value.includes(' ') && value.length <= 5 && (!suffix || value.toUpperCase() === suffix)
}

function answerDomainCode(answer, fallbackCode = '') {
  const explicitCode = normalizeDomainCode(answer?.domainCode)
  const questionCode = normalizeDomainCode(domainCodeFromQuestionCode(answer?.questionCode))
  return normalizeDomainCode(firstDefined(questionCode, explicitCode, fallbackCode))
}

function answerDomainTitle(answer, code) {
  return normalizeDomainTitle(code, answer?.domainTitle)
}

function splitSegmentByAnswerDomain(segment) {
  const directGroups = new Map()
  for (const answer of segment.answers ?? []) {
    const code = answerDomainCode(answer, segment.segmentCode)
    if (!directGroups.has(code)) directGroups.set(code, [])
    directGroups.get(code).push(answer)
  }

  const subDomainGroups = new Map()
  for (const sub of segment.subDomains ?? []) {
    const answersByCode = new Map()
    for (const answer of sub.answers ?? []) {
      const code = answerDomainCode(answer, segment.segmentCode)
      if (!answersByCode.has(code)) answersByCode.set(code, [])
      answersByCode.get(code).push(answer)
    }

    for (const [code, answers] of answersByCode) {
      if (!subDomainGroups.has(code)) subDomainGroups.set(code, [])
      subDomainGroups.get(code).push({ ...sub, answers })
    }
  }

  const codes = new Set([...directGroups.keys(), ...subDomainGroups.keys()].filter(Boolean))
  if (codes.size <= 1 && (codes.has(segment.segmentCode) || codes.size === 0)) return [segment]

  return [...codes].map((code) => {
    const answers = directGroups.get(code) ?? []
    const subDomains = subDomainGroups.get(code) ?? []
    const firstAnswer = answers[0] ?? subDomains.flatMap((sub) => sub.answers ?? [])[0] ?? null
    const sameAsOriginal = code === segment.segmentCode
    const nextSegment = {
      ...segment,
      id: sameAsOriginal ? segment.id : code,
      segmentCode: code,
      segmentTitle:
        sameAsOriginal && !isAbbreviatedTitle(segment.segmentTitle, code)
          ? segment.segmentTitle
          : titleFromAnswers([...answers, ...subDomains.flatMap((sub) => sub.answers ?? [])], code) ||
            answerDomainTitle(firstAnswer, code),
      answers,
      subDomains,
    }
    const score = clientLikeSegmentScore(nextSegment, sameAsOriginal ? segment.score : null)

    return {
      ...nextSegment,
      score,
      averageScore: displayAverageScore(nextSegment),
      maturityLabel:
        sameAsOriginal && segment.maturityLabel
          ? segment.maturityLabel
          : score === null
            ? ''
            : maturityLabelForScore(frameworkKeyFromSegment(nextSegment), score),
    }
  })
}

function splitSegmentsByAnswerDomain(segments) {
  return (segments ?? []).flatMap(splitSegmentByAnswerDomain).map((segment) => {
    if (!isAbbreviatedTitle(segment.segmentTitle, segment.segmentCode)) return segment
    const title = titleFromAnswers(collectSegmentAnswers(segment), segment.segmentCode)
    return {
      ...segment,
      segmentTitle: title || normalizeDomainTitle(segment.segmentCode, segment.segmentTitle),
    }
  })
}

function groupCMMISegments(segments) {
  const result = []
  const groups = new Map()

  for (const segment of segments ?? []) {
    const parts = cmmiCodeParts(segment.segmentCode)
    if (!parts) {
      result.push(segment)
      continue
    }

    const parentCode = `cmmi_${parts.major}`
    if (!groups.has(parentCode)) {
      const parent = {
        ...segment,
        id: parentCode,
        segmentCode: parentCode,
        segmentTitle: CMMI_PARENT_DOMAIN_TITLES[parts.major] ?? segment.segmentTitle,
        answers: [],
        subDomains: [],
      }
      groups.set(parentCode, parent)
      result.push(parent)
    }

    const parent = groups.get(parentCode)
    parent.subDomains.push({
      id: segment.id,
      code: segment.segmentCode,
      name: cmmiSubDomainName(segment),
      sortOrder: Number(parts.minor),
      answers: collectSegmentAnswers(segment),
    })

    parent.score = clientLikeSegmentScore(parent, null)
    parent.averageScore = displayAverageScore(parent)
    parent.maturityLabel = parent.score === null ? '' : maturityLabelForScore('cmmi', parent.score)
  }

  return result.map((segment) => {
    if (!segment.segmentCode?.startsWith?.('cmmi_')) return segment
    return {
      ...segment,
      subDomains: [...(segment.subDomains ?? [])].sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0)),
    }
  })
}

const DOMAIN_ARRAY_FIELDS = [
  'segments',
  'domains',
  'domainList',
  'domainScores',
  'domainResults',
  'frameworkDomains',
]

const OBJECT_CONTAINER_FIELDS = [
  'assessment',
  'detail',
  'result',
  'data',
  'payload',
  'framework',
  'evaluationFramework',
  'questionnaire',
  'project',
]

const ARRAY_CONTAINER_FIELDS = [
  'frameworks',
  'allowedFrameworks',
  'assignedFrameworks',
  'projectFrameworks',
  'assessments',
  'versions',
]

function hasQuestionOrSubdomainContent(row) {
  return (
    Array.isArray(row?.answers) ||
    Array.isArray(row?.questions) ||
    Array.isArray(row?.subDomains) ||
    Array.isArray(row?.subdomains)
  )
}

function bestCandidate(candidates) {
  return candidates.reduce((best, rows) => (rows.length > best.length ? rows : best), [])
}

function collectDomainCandidates(source, depth = 0) {
  if (!source || typeof source !== 'object' || depth > 4) return []

  const candidates = []
  for (const field of DOMAIN_ARRAY_FIELDS) {
    const rows = asArray(source[field])
    if (rows.length) candidates.push(expandDomainRows(rows, depth + 1))
  }

  for (const field of OBJECT_CONTAINER_FIELDS) {
    if (source[field] && typeof source[field] === 'object') {
      candidates.push(...collectDomainCandidates(source[field], depth + 1))
    }
  }

  for (const field of ARRAY_CONTAINER_FIELDS) {
    for (const item of asArray(source[field])) {
      candidates.push(...collectDomainCandidates(item, depth + 1))
    }
  }

  return candidates.filter((rows) => rows.length > 0)
}

function expandDomainRows(rows, depth = 0) {
  return rows.flatMap((row) => {
    const nestedRows = bestCandidate(collectDomainCandidates(row, depth + 1))
    if (nestedRows.length > 0 && !hasQuestionOrSubdomainContent(row)) return nestedRows
    return [row]
  })
}

function normalizeSegment(raw, index) {
  const code = normalizeDomainCode(firstDefined(raw?.segmentCode, raw?.code, raw?.domainCode, `DOMAIN_${index + 1}`))
  const id = firstDefined(raw?.id, raw?.segmentId, raw?.domainId, code)
  const rawTitle = firstDefined(raw?.segmentTitle, raw?.name, raw?.title, raw?.domainName, code)
  const title = normalizeDomainTitle(code, rawTitle)
  const subDomains = asArray(raw?.subDomains ?? raw?.subdomains)
  const directQuestions = asArray(raw?.answers ?? raw?.questions)
  const directScore = roundScore(
    firstDefined(
      raw?.score,
      raw?.domainScore,
      raw?.domain_score,
    ),
  )
  const backendAverageScore = roundScore(
    firstDefined(raw?.averageScore, raw?.average_score, raw?.avgScore, raw?.avg_score),
  )
  const frameworkKey = frameworkKeyFromSegment(raw)

  const segment = {
    id,
    segmentCode: code,
    segmentTitle: title,
    score: directScore,
    weight: toFiniteNumber(firstDefined(raw?.weight, raw?.domainWeight, raw?.domain_weight)) ?? null,
    maturityLabel: firstDefined(raw?.maturityLabel, raw?.label, ''),
    answers: directQuestions.map((q, qIndex) => normalizeAnswer(q, `${code}-${qIndex + 1}`)),
    subDomains: subDomains.map((sd, sdIndex) => {
      const subName = normalizeSubDomainName(sd, sdIndex)
      return {
        name: subName,
        answers: asArray(sd?.questions ?? sd?.answers).map((q, qIndex) =>
          normalizeAnswer(q, `${code}-${sdIndex + 1}-${qIndex + 1}`),
        ),
      }
    }),
  }

  const score = clientLikeSegmentScore(segment, directScore)
  return {
    ...segment,
    score,
    averageScore: backendAverageScore ?? displayAverageScore(segment),
    maturityLabel: segment.maturityLabel || (score === null ? '' : maturityLabelForScore(frameworkKey, score)),
  }
}

function pickDomainRows(data) {
  return bestCandidate(collectDomainCandidates(data))
}

function computeFrameworkAvg(segments) {
  const rows = (segments ?? [])
    .map((seg) => ({
      score: toFiniteNumber(seg.score),
      weight: toFiniteNumber(seg.weight) ?? 1,
    }))
    .filter((row) => row.score !== null)

  if (!rows.length) return null
  const weightedTotal = rows.reduce((sum, row) => sum + row.score * row.weight, 0)
  const totalWeight = rows.reduce((sum, row) => sum + row.weight, 0)
  return totalWeight > 0 ? roundScore(weightedTotal / totalWeight) : null
}

function computeFrameworkAverageScore(segments) {
  const rows = (segments ?? [])
    .map((seg) => ({
      score: toFiniteNumber(seg.averageScore),
      weight: toFiniteNumber(seg.weight) ?? 1,
    }))
    .filter((row) => row.score !== null)

  if (!rows.length) return null
  const weightedTotal = rows.reduce((sum, row) => sum + row.score * row.weight, 0)
  const totalWeight = rows.reduce((sum, row) => sum + row.weight, 0)
  return totalWeight > 0 ? roundScore(weightedTotal / totalWeight) : null
}

function computeFrameworkAverages(segments) {
  const groups = new Map()
  for (const seg of segments ?? []) {
    const key = frameworkKeyFromSegment(seg) || 'unknown'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(seg)
  }

  return [...groups.entries()].map(([key, rows]) => ({
    key,
    label: frameworkLabelFromKey(key),
    avg: computeFrameworkAvg(rows),
    averageScore: computeFrameworkAverageScore(rows),
    domainScores: rows.map((seg) => ({
      code: seg.segmentCode,
      title: seg.segmentTitle,
      score: seg.score,
      averageScore: seg.averageScore,
      weight: seg.weight ?? 1,
    })),
  }))
}

/** Map various backend shapes into a single “assessment-like” object for the UI. */
export function normalizeVersionDetail(data) {
  if (!data || typeof data !== 'object') return null
  const scoringSegments = splitSegmentsByAnswerDomain(pickDomainRows(data).map((d, i) => normalizeSegment(d, i)))
  const segments = groupCMMISegments(scoringSegments)
  const frameworkAverages = computeFrameworkAverages(scoringSegments)
  const computedFrameworkAvg = frameworkAverages.length === 1 ? frameworkAverages[0].avg : null
  const computedFrameworkAverageScore = frameworkAverages.length === 1 ? frameworkAverages[0].averageScore : null
  const computedGlobalAverageScore = computeFrameworkAverageScore(scoringSegments)
  const backendFrameworkAvg = roundScore(
    firstDefined(
      data.frameworkAvg,
      data.frameworkAVG,
      data.framework_avg,
      data.frameworkScore,
      data.framework_score,
    ),
  )
  const frameworkAvg = computedFrameworkAvg ?? backendFrameworkAvg
  const globalAverageScore = roundScore(
    firstDefined(data.globalAverageScore, data.global_average_score, computedGlobalAverageScore),
  )
  const frameworkAverageScore = roundScore(
    firstDefined(
      computedFrameworkAverageScore,
      frameworkAverages.length === 1
        ? firstDefined(
            data.frameworkAverageScore,
            data.framework_average_score,
            (data.frameworkStatus ?? data.frameworkDetails ?? [])[0]?.frameworkAverageScore,
          )
        : null,
      globalAverageScore,
    ),
  )
  const frameworkKey =
    frameworkKeyFromValue(data.frameworkKey ?? data.frameworkCode ?? data.framework ?? data.frameworkName) ||
    segments.map(frameworkKeyFromSegment).find(Boolean) ||
    ''
  const frameworkMaturityLabel = firstDefined(
    data.frameworkMaturityLabel,
    data.frameworkLabel,
    frameworkAvg === null ? '' : maturityLabelForScore(frameworkKey, frameworkAvg),
  )

  console.debug('[Assessment AVG][admin]', {
    backendFrameworkAvg,
    displayedFrameworkAvg: frameworkAvg,
    globalAverageScore,
    frameworkAverageScore,
    frameworkAverages,
    formula: 'weighted average of domain scores / domain average scores per framework',
  })

  return {
    id: data.id ?? data.assessmentId ?? data.versionId,
    globalScore: data.globalScore ?? data.score,
    globalAverageScore,
    globalMaturityLabel: data.globalMaturityLabel ?? data.maturityLabel,
    frameworkAvg,
    frameworkAverageScore,
    frameworkAverages,
    frameworkMaturityLabel,
    status: data.status,
    globalStatus: data.globalStatus ?? data.status,
    frameworkStatus: normalizeFrameworkStatusList(data.frameworkStatus ?? data.frameworkDetails),
    year: data.year,
    version: data.versionNumber ?? data.version,
    submittedAt: data.submittedAt ?? data.submitted_at,
    versionComment: data.versionComment ?? data.submissionComment ?? data.comment ?? data.version_comment ?? null,
    segments,
  }
}

export function flattenAnswersForDiff(assessment) {
  const rows = []
  if (!assessment?.segments) return rows
  for (const seg of assessment.segments) {
    const domainLabel = `${seg.segmentTitle ?? ''} (${seg.segmentCode ?? ''})`.trim()
    for (const ans of seg.answers ?? []) {
      const key = `${seg.segmentCode ?? ''}::${ans.questionCode ?? ''}`
      rows.push({
        key,
        domainLabel,
        questionCode: ans.questionCode,
        questionText: ans.questionText,
        score: ans.score,
        evidenceId: ans.evidenceId,
        evidenceFileName: ans.evidenceFileName,
        evidences: ans.evidences ?? [],
        note: ans.note ?? ans.comment ?? '',
        evidenceStaffRating: ans.evidenceStaffRating,
        evidenceStaffComment: ans.evidenceStaffComment ?? ans.staffComment ?? '',
      })
    }
    for (const sub of seg.subDomains ?? []) {
      const subLabel = sub.name ?? sub.title ?? 'Sub-domain'
      for (const ans of sub.answers ?? []) {
        const key = `${seg.segmentCode ?? ''}::${subLabel}::${ans.questionCode ?? ''}`
        rows.push({
          key,
          domainLabel: `${domainLabel} → ${subLabel}`,
          questionCode: ans.questionCode,
          questionText: ans.questionText,
          score: ans.score,
          evidenceId: ans.evidenceId,
          evidenceFileName: ans.evidenceFileName,
          evidences: ans.evidences ?? [],
          note: ans.note ?? ans.comment ?? '',
          evidenceStaffRating: ans.evidenceStaffRating,
          evidenceStaffComment: ans.evidenceStaffComment ?? ans.staffComment ?? '',
        })
      }
    }
  }
  return rows
}

function normalizeDiffString(value) {
  return String(value ?? '').trim()
}

function normalizeDiffScore(value) {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  return Number.isFinite(n) ? String(n) : normalizeDiffString(value)
}

function normalizeEvidenceName(value) {
  return normalizeDiffString(value).replaceAll('\\', '/').split('/').pop().toLowerCase()
}

function normalizeEvidenceSignature(row) {
  const names = (row?.evidences ?? [])
    .map((item) => normalizeEvidenceName(item?.fileName ?? item?.originalFileName ?? item?.evidenceFileName ?? item?.name))
    .filter(Boolean)
  const fallback = normalizeEvidenceName(row?.evidenceFileName)
  if (names.length === 0 && fallback) names.push(fallback)
  return [...new Set(names)].sort().join('|')
}

function normalizeDiffRating(value) {
  return normalizeDiffString(value).toUpperCase()
}

function answerDiffSignature(row) {
  return {
    score: normalizeDiffScore(row?.score),
    note: normalizeDiffString(row?.note),
    evidenceFileName: normalizeEvidenceSignature(row),
    evidenceStaffRating: normalizeDiffRating(row?.evidenceStaffRating),
    evidenceStaffComment: normalizeDiffString(row?.evidenceStaffComment),
  }
}

function answerHasRealDiff(oldRow, newRow) {
  const oldSig = answerDiffSignature(oldRow)
  const newSig = answerDiffSignature(newRow)
  return Object.keys(oldSig).some((key) => oldSig[key] !== newSig[key])
}

export function computeVersionDiff(olderAssessment, newerAssessment) {
  const oldRows = flattenAnswersForDiff(olderAssessment)
  const newRows = flattenAnswersForDiff(newerAssessment)
  const oldMap = new Map(oldRows.map((r) => [r.key, r]))
  const newMap = new Map(newRows.map((r) => [r.key, r]))
  const keys = new Set([...oldMap.keys(), ...newMap.keys()])
  const changes = []
  for (const key of keys) {
    const o = oldMap.get(key)
    const n = newMap.get(key)
    if (o && !n) {
      changes.push({ key, type: 'Deleted', ...buildChangeCells(o, null) })
      continue
    }
    if (!o && n) {
      changes.push({ key, type: 'Added', ...buildChangeCells(null, n) })
      continue
    }
    if (o && n) {
      if (answerHasRealDiff(o, n)) {
        changes.push({ key, type: 'Modified', ...buildChangeCells(o, n) })
      }
    }
  }
  return changes.sort((a, b) => a.domainLabel.localeCompare(b.domainLabel) || a.questionCode.localeCompare(b.questionCode))
}

function buildChangeCells(o, n) {
  const oldSig = answerDiffSignature(o)
  const newSig = answerDiffSignature(n)
  const changeReasons = [
    oldSig.score !== newSig.score ? 'score' : null,
    oldSig.note !== newSig.note ? 'note' : null,
    oldSig.evidenceFileName !== newSig.evidenceFileName ? 'evidence' : null,
    oldSig.evidenceStaffRating !== newSig.evidenceStaffRating ? 'rating' : null,
    oldSig.evidenceStaffComment !== newSig.evidenceStaffComment ? 'staff comment' : null,
  ].filter(Boolean)
  return {
    domainLabel: n?.domainLabel ?? o?.domainLabel ?? '',
    questionCode: n?.questionCode ?? o?.questionCode ?? '',
    questionText: n?.questionText ?? o?.questionText ?? '',
    oldScore: o?.score ?? null,
    newScore: n?.score ?? null,
    oldEvidence: o?.evidenceFileName ?? (o?.evidenceId ? `#${o.evidenceId}` : '—'),
    newEvidence: n?.evidenceFileName ?? (n?.evidenceId ? `#${n.evidenceId}` : '—'),
    changeReasons,
  }
}
