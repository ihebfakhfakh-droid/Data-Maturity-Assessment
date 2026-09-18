import { useEffect, useState } from 'react'
import { Download, Loader2, Sparkles, Upload } from 'lucide-react'
import { EvidenceDeleteConfirmModal, EvidenceFilesPanel } from '../../components/EvidenceFilesPanel.jsx'

export function maturityLabelEn(label) {
  const value = String(label ?? '').trim()
  if (!value) return ''
  const normalized = value.toLowerCase()
  return (
    {
      'absence de capacités': 'Absence of capabilities',
      'absence de capacites': 'Absence of capabilities',
      'en cours d’établissement': 'Establishing',
      "en cours d'etablissement": 'Establishing',
      défini: 'Defined',
      defini: 'Defined',
      activé: 'Activated',
      active: 'Activated',
      maîtrisé: 'Managed',
      maitrise: 'Managed',
      pionnier: 'Pioneer',
      'non répondu': 'Not answered',
      'non repondu': 'Not answered',
      'non mis en place': 'Not implemented',
      optimisé: 'Optimized',
      optimise: 'Optimized',
    }[normalized] ?? value
  )
}

export function evidenceItemsForAnswer(ans) {
  const items = Array.isArray(ans?.evidences) ? ans.evidences : []
  if (items.length > 0) {
    return items
      .map((item) => ({
        id: item?.id ?? item?.evidenceId,
        fileName: item?.fileName ?? item?.originalFileName ?? item?.evidenceFileName ?? '',
        sizeBytes: item?.sizeBytes ?? item?.size ?? item?.fileSize ?? null,
      }))
      .filter((item) => item.id)
  }
  return ans?.evidenceId
    ? [
        {
          id: ans.evidenceId,
          fileName: ans.evidenceFileName ?? `Evidence ${ans.evidenceId}`,
          sizeBytes: ans.evidenceSizeBytes ?? ans.sizeBytes ?? null,
        },
      ]
    : []
}

async function downloadEvidence(evidenceId, token) {
  const res = await fetch(`/api/admin/evidences/${evidenceId}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Download failed: ${res.status} ${res.statusText}${text ? ` - ${text}` : ''}`)
  }
  const blob = await res.blob()
  const cd = res.headers.get('content-disposition') ?? ''
  const m = cd.match(/filename="?([^";]+)"?/i)
  const fileName = m?.[1] ?? `evidence-${evidenceId}`
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

async function downloadEvidences(items, token) {
  for (const item of items) {
    await downloadEvidence(item.id ?? item.evidenceId, token)
  }
}

function answerComment(ans) {
  const value = ans?.comment ?? ans?.note ?? ''
  return String(value ?? '').trim()
}

function assessmentDomainKey(seg, segIndex) {
  return String(seg?.id ?? seg?.segmentCode ?? `domain-${segIndex}`)
}

function assessmentDomainAnswers(seg) {
  return [
    ...(seg?.answers ?? []),
    ...(seg?.subDomains ?? []).flatMap((sub) => sub?.answers ?? []),
  ]
}

function assessmentAnswerIsAnswered(ans) {
  if (ans?.answered === true || ans?.isAnswered === true) return true
  if (ans?.answered === false || ans?.isAnswered === false) return false
  if (ans?.selectedScore !== null && ans?.selectedScore !== undefined) return true
  if (ans?.score !== null && ans?.score !== undefined && ans?.score !== '') return true
  return Boolean(ans?.answeredAt ?? ans?.answered_at)
}

function assessmentDomainQuestionCount(seg) {
  return assessmentDomainAnswers(seg).length
}

function assessmentDomainAnsweredCount(seg) {
  return assessmentDomainAnswers(seg).filter(assessmentAnswerIsAnswered).length
}

function assessmentDomainState(seg) {
  const total = assessmentDomainQuestionCount(seg)
  if (total === 0) return 'Not answered'
  return assessmentDomainAnsweredCount(seg) === total ? 'Answered' : 'Not answered'
}

function assessmentSubdomainKey(domainId, sub, subIndex) {
  return `${domainId}::${sub?.id ?? sub?.code ?? sub?.name ?? subIndex}`
}

function assessmentSubdomainAnsweredCount(sub) {
  return (sub?.answers ?? []).filter(assessmentAnswerIsAnswered).length
}

function assessmentSubdomainState(sub) {
  const total = (sub?.answers ?? []).length
  if (total === 0) return 'Not answered'
  return assessmentSubdomainAnsweredCount(sub) === total ? 'Answered' : 'Not answered'
}

export function AssessmentDetailsDomains({
  segments = [],
  recommendations = [],
  assessmentId = null,
  token = '',
  interactive = false,
  onUploadEvidence,
  onRateEvidence,
  onAcceptanceCriteriaReport,
  canUseAcceptanceCriteria = false,
  onDeleteEvidence,
  canDeleteEvidence = false,
  onError,
  onSuccess,
}) {
  const [expandedDomainIds, setExpandedDomainIds] = useState(() => new Set())
  const [expandedSubdomainIds, setExpandedSubdomainIds] = useState(() => new Set())
  const [acceptanceCriteriaLoadingId, setAcceptanceCriteriaLoadingId] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    setExpandedDomainIds(new Set())
    setExpandedSubdomainIds(new Set())
  }, [assessmentId])

  function toggleDomain(domainId) {
    setExpandedDomainIds((prev) => {
      const next = new Set(prev)
      if (next.has(domainId)) {
        next.delete(domainId)
      } else {
        next.add(domainId)
      }
      return next
    })
  }

  function toggleSubdomain(subdomainId) {
    setExpandedSubdomainIds((prev) => {
      const next = new Set(prev)
      if (next.has(subdomainId)) {
        next.delete(subdomainId)
      } else {
        next.add(subdomainId)
      }
      return next
    })
  }

  function reportError(err) {
    onError?.(err?.message ?? String(err))
  }

  async function confirmDeleteEvidence() {
    if (!pendingDelete?.id || typeof onDeleteEvidence !== 'function') return
    const evidenceId = pendingDelete.id
    setDeletingId(evidenceId)
    try {
      await onDeleteEvidence(evidenceId)
      onSuccess?.(`Evidence deleted${pendingDelete.fileName ? `: ${pendingDelete.fileName}` : ''}.`)
      setPendingDelete(null)
    } catch (err) {
      reportError(err)
    } finally {
      setDeletingId(null)
    }
  }

  function renderAnswerRow(ans, keyPrefix = '') {
    const evidenceItems = evidenceItemsForAnswer(ans)
    const firstEvidence = evidenceItems[0] ?? null
    const comment = answerComment(ans)
    const staffComment = String(ans?.evidenceStaffComment ?? ans?.staffComment ?? '').trim()
    const allowDelete = Boolean(canDeleteEvidence && interactive && typeof onDeleteEvidence === 'function')

    return (
      <div key={`${keyPrefix}${ans.questionCode}`} className="answerRow">
        <div className="qText">
          <div className="qCode">{ans.questionCode}</div>
          <div className="adminQuestionText">{ans.questionText}</div>
          {comment ? <div className="tinyNote">Comment: {comment}</div> : null}
          {staffComment ? <div className="tinyNote">Staff note: {staffComment}</div> : null}
          <EvidenceFilesPanel
            answerId={ans.questionCode ?? keyPrefix}
            items={evidenceItems}
            canDelete={allowDelete}
            deletingId={deletingId}
            onRequestDelete={(item) => setPendingDelete(item)}
            emptyLabel="No evidence"
          />

          <div className="evidenceActions evidenceActionsStart" style={{ marginTop: 8 }}>
            {evidenceItems.length > 0 ? (
              <button
                type="button"
                className="iconBtn btnWithIcon"
                title="Download all evidences"
                aria-label="Download all evidences"
                onClick={async () => {
                  try {
                    await downloadEvidences(evidenceItems, token)
                  } catch (err) {
                    reportError(err)
                  }
                }}
              >
                <Download size={16} strokeWidth={2.2} aria-hidden="true" />
              </button>
            ) : null}

            {interactive && assessmentId && onUploadEvidence ? (
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
                      await onUploadEvidence(assessmentId, ans.questionCode, ans.score, files)
                    } catch (err) {
                      reportError(err)
                    }
                  }}
                />
                <span className="uploadEvidenceIcon" aria-hidden="true">
                  <Upload size={16} strokeWidth={2.2} />
                </span>
                <span>Upload Evidence</span>
              </label>
            ) : null}

            {interactive && firstEvidence && (onRateEvidence || (canUseAcceptanceCriteria && typeof onAcceptanceCriteriaReport === 'function')) ? (
              <div className="evidenceRatingActions">
                {onRateEvidence ? (
                  <div className="confidenceGroup" aria-label="Evidence confidence">
                    {[
                      { key: 'LOW', label: 'Low' },
                      { key: 'MEDIUM', label: 'Med' },
                      { key: 'HIGH', label: 'High' },
                    ].map((opt) => {
                      const active = String(ans.evidenceStaffRating ?? '').toUpperCase() === opt.key
                      return (
                        <button
                          key={opt.key}
                          type="button"
                          className={
                            active
                              ? `confidenceBtn confidenceBtnActive confidenceBtn${opt.key}`
                              : `confidenceBtn confidenceBtn${opt.key}`
                          }
                          title={`Evidence confidence: ${opt.label}`}
                          onClick={async () => {
                            try {
                              await onRateEvidence(firstEvidence.id, opt.key)
                            } catch (err) {
                              reportError(err)
                            }
                          }}
                        >
                          {opt.label}
                        </button>
                      )
                    })}
                  </div>
                ) : null}

                {canUseAcceptanceCriteria && typeof onAcceptanceCriteriaReport === 'function' ? (
                  <button
                    type="button"
                    className={
                      String(acceptanceCriteriaLoadingId) === String(firstEvidence.id)
                        ? 'acceptanceCriteriaBtn acceptanceCriteriaBtnLoading'
                        : 'acceptanceCriteriaBtn'
                    }
                    title="Acceptance Criteria"
                    aria-label="Acceptance Criteria"
                    disabled={acceptanceCriteriaLoadingId != null}
                    onClick={async () => {
                      if (acceptanceCriteriaLoadingId != null) return
                      const evidenceId = firstEvidence.id
                      setAcceptanceCriteriaLoadingId(evidenceId)
                      try {
                        await onAcceptanceCriteriaReport(evidenceId)
                      } catch (err) {
                        reportError(err)
                      } finally {
                        setAcceptanceCriteriaLoadingId(null)
                      }
                    }}
                  >
                    {String(acceptanceCriteriaLoadingId) === String(firstEvidence.id) ? (
                      <Loader2 size={15} strokeWidth={2.4} className="acceptanceCriteriaSpinner" aria-hidden="true" />
                    ) : (
                      <Sparkles size={15} strokeWidth={2.2} aria-hidden="true" />
                    )}
                    <span className="acceptanceCriteriaBtnLabel">
                      {String(acceptanceCriteriaLoadingId) === String(firstEvidence.id)
                        ? 'Generating report...'
                        : 'Acceptance Criteria'}
                    </span>
                    {String(acceptanceCriteriaLoadingId) === String(firstEvidence.id) ? null : (
                      <Download size={15} strokeWidth={2.2} aria-hidden="true" />
                    )}
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
        <div className="answerScore">
          <strong>{ans.score ?? '—'}</strong>/5
        </div>
      </div>
    )
  }

  return (
    <div className="stack">
      {Array.isArray(recommendations) && recommendations.length > 0 ? (
        <div className="qItem">
          <div className="listTitle">Recommendations</div>
          <ul>
            {recommendations.map((rec, index) => (
              <li key={`${String(rec)}-${index}`}>{String(rec)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {segments.map((seg, segIndex) => {
        const domainId = assessmentDomainKey(seg, segIndex)
        const expanded = expandedDomainIds.has(domainId)
        const questionCount = assessmentDomainQuestionCount(seg)
        const answeredCount = assessmentDomainAnsweredCount(seg)
        const domainState = assessmentDomainState(seg)
        const subDomainsWithAnswers = (seg.subDomains ?? []).filter((sub) => (sub.answers ?? []).length > 0)

        return (
          <div key={domainId} className={expanded ? 'assessmentDomainCard assessmentDomainCardOpen' : 'assessmentDomainCard'}>
            <button
              type="button"
              className="assessmentDomainToggle"
              aria-expanded={expanded}
              onClick={() => toggleDomain(domainId)}
            >
              <span className="assessmentDomainChevron" aria-hidden="true">
                {expanded ? '▼' : '▶'}
              </span>
              <span className="assessmentDomainMain">
                <span className="assessmentDomainTitle">{seg.segmentTitle ?? 'Domain'}</span>
                <span className="qCode">{seg.segmentCode ?? `DOMAIN_${segIndex + 1}`}</span>
              </span>
              <span className="assessmentDomainMetrics">
                <span className="badge">Domain score {seg.score ?? '—'} / 5</span>
                <span className="badge" title="Domain average for display only">
                  Domain avg {seg.averageScore ?? '—'} / 5
                </span>
                <span className="badge">
                  {answeredCount}/{questionCount} questions
                </span>
                <span className={domainState === 'Answered' ? 'badge badgeSuccess' : 'badge badgeNeutral'}>
                  {domainState}
                </span>
              </span>
            </button>

            {expanded ? (
              <div className="assessmentDomainPanel">
                {seg.maturityLabel ? (
                  <div className="tinyNote">Maturity: {maturityLabelEn(seg.maturityLabel)}</div>
                ) : null}
                {subDomainsWithAnswers.length > 0 ? (
                  <div className="assessmentSubdomainList">
                    {subDomainsWithAnswers.map((sub, subIndex) => {
                      const subdomainId = assessmentSubdomainKey(domainId, sub, subIndex)
                      const subExpanded = expandedSubdomainIds.has(subdomainId)
                      const subQuestionCount = (sub.answers ?? []).length
                      const subAnsweredCount = assessmentSubdomainAnsweredCount(sub)
                      const subState = assessmentSubdomainState(sub)

                      return (
                        <div
                          key={subdomainId}
                          className={subExpanded ? 'assessmentSubdomainCard assessmentSubdomainCardOpen' : 'assessmentSubdomainCard'}
                        >
                          <button
                            type="button"
                            className="assessmentSubdomainToggle"
                            aria-expanded={subExpanded}
                            onClick={() => toggleSubdomain(subdomainId)}
                          >
                            <span className="assessmentDomainChevron" aria-hidden="true">
                              {subExpanded ? '▼' : '▶'}
                            </span>
                            <span className="assessmentDomainMain">
                              <span className="assessmentDomainTitle">{sub.name ?? sub.title ?? `Subdomain ${subIndex + 1}`}</span>
                              {sub.code ? <span className="qCode">{sub.code}</span> : null}
                            </span>
                            <span className="assessmentDomainMetrics">
                              <span className="badge">
                                {subAnsweredCount}/{subQuestionCount} questions
                              </span>
                              <span className={subState === 'Answered' ? 'badge badgeSuccess' : 'badge badgeNeutral'}>
                                {subState}
                              </span>
                            </span>
                          </button>

                          {subExpanded ? (
                            <div className="assessmentSubdomainPanel">
                              {(sub.answers ?? []).map((ans) =>
                                renderAnswerRow(ans, `${seg.segmentCode ?? `domain-${segIndex}`}-sub-${subIndex}-`),
                              )}
                            </div>
                          ) : null}
                        </div>
                      )
                    })}
                  </div>
                ) : null}

                {subDomainsWithAnswers.length === 0 && (seg.answers ?? []).length > 0 ? (
                  <div style={{ display: 'grid', gap: 8 }}>
                    {(seg.answers ?? []).map((ans) => renderAnswerRow(ans, `${seg.segmentCode ?? `domain-${segIndex}`}-`))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        )
      })}
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
