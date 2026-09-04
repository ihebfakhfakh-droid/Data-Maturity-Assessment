import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { GitCompareArrows, History, Layers3, X } from 'lucide-react'
import { apiFetch } from '../../api/client.js'
import { exportAssessmentPdf, isSubmittedAssessment } from '../../utils/assessmentPdf.js'
import { AssessmentDetailsDomains, maturityLabelEn } from './AssessmentDetailsDomains.jsx'
import { buildAdminAssessmentPdfReport } from './assessmentPdfReport.js'
import {
  assessmentVersionDetailPath,
  assessmentVersionsListPath,
  computeVersionDiff,
  markLatestVersion,
  normalizeVersionDetail,
  normalizeVersionRow,
} from './assessmentVersioningApi.js'

function parseVersionsResponse(raw) {
  if (Array.isArray(raw)) return raw
  if (raw?.content && Array.isArray(raw.content)) return raw.content
  if (raw?.items && Array.isArray(raw.items)) return raw.items
  if (raw?.versions && Array.isArray(raw.versions)) return raw.versions
  return []
}

function changeBadgeClass(type) {
  if (type === 'Added') return 'verBadge verBadgeAdded'
  if (type === 'Deleted') return 'verBadge verBadgeDeleted'
  return 'verBadge verBadgeModified'
}

function frameworkStatusLabel(item) {
  const status = String(item?.frameworkStatus ?? '').toUpperCase()
  if (status === 'SUBMITTED') return 'Submitted'
  if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'Current Assessment'
  return status || '—'
}

function assessmentStatusLabel(value) {
  const status = String(value ?? '').toUpperCase()
  if (status === 'SUBMITTED') return 'Submitted'
  if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'Current Assessment'
  return status || '—'
}

function statusBadgeClass(value) {
  const status = String(value ?? '').toUpperCase()
  if (status === 'SUBMITTED') return 'verBadge verBadgeSubmitted'
  if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'verBadge verBadgeCurrent'
  return 'verBadge verBadgeNeutral'
}

function formatDateParts(iso) {
  if (!iso) return { date: '—', time: '' }
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return { date: String(iso), time: '' }
    return {
      date: d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }),
      time: d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
    }
  } catch {
    return { date: String(iso), time: '' }
  }
}

function formatDate(iso) {
  const parts = formatDateParts(iso)
  return parts.time ? `${parts.date} ${parts.time}` : parts.date
}

function pickLatestVersion(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return null
  const marked = rows.find((row) => row.isLatest)
  if (marked) return marked
  return [...rows].sort((a, b) => Number(b.versionNumber) - Number(a.versionNumber))[0] ?? null
}

function ScoreCell({ value }) {
  if (value == null) return <span className="verScoreEmpty">—</span>
  return (
    <span className="verScoreCell">
      <strong>{value}</strong>
      <span className="verScoreSuffix"> / 5</span>
    </span>
  )
}

function FrameworkCell({ rows }) {
  if (!rows?.length) return <span className="muted">—</span>
  return (
    <div className="verFrameworkStack">
      {rows.map((item) => (
        <div key={item.frameworkCode} className="verFrameworkItem">
          <span className="verFrameworkBadge">{item.frameworkCode}</span>
          <span className="verFrameworkMeta">
            {item.answeredQuestions}/{item.totalQuestions}
          </span>
        </div>
      ))}
    </div>
  )
}

export function AssessmentVersioningOverlay({ clientId, clientLabel, token, onClose }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token])
  const titleId = useId()
  const dialogRef = useRef(null)
  const closeBtnRef = useRef(null)
  const previouslyFocusedRef = useRef(null)

  const [loadError, setLoadError] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [versions, setVersions] = useState([])

  const [selectedVersionId, setSelectedVersionId] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [detail, setDetail] = useState(null)

  const [baselineId, setBaselineId] = useState('')
  const [currentId, setCurrentId] = useState('')
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState('')
  const [compareRows, setCompareRows] = useState([])
  const [exportingPdf, setExportingPdf] = useState(false)
  const [exportError, setExportError] = useState('')

  const latestVersion = useMemo(() => pickLatestVersion(versions), [versions])
  const canExportAssessmentPdf = Boolean(
    latestVersion &&
      isSubmittedAssessment({
        status: latestVersion.status,
      }),
  )

  const reloadList = useCallback(async () => {
    setLoadError('')
    setLoadingList(true)
    try {
      const raw = await apiFetch(assessmentVersionsListPath(clientId), { headers })
      const arr = parseVersionsResponse(raw)
      const mapped = markLatestVersion(arr.map((v, i) => normalizeVersionRow(v, i)))
      setVersions(mapped)
      setSelectedVersionId(null)
      setDetail(null)
    } catch (e) {
      setLoadError(e?.message ?? 'Could not load assessment versions')
      setVersions([])
    } finally {
      setLoadingList(false)
    }
  }, [clientId, headers])

  useEffect(() => {
    reloadList()
  }, [reloadList])

  useEffect(() => {
    previouslyFocusedRef.current = document.activeElement
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const timer = window.setTimeout(() => {
      closeBtnRef.current?.focus()
    }, 0)

    function onKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose?.()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      const previous = previouslyFocusedRef.current
      if (previous && typeof previous.focus === 'function') {
        previous.focus()
      }
    }
  }, [onClose])

  const loadDetail = useCallback(
    async (versionId) => {
      if (!versionId) return
      setDetailError('')
      setDetailLoading(true)
      setDetail(null)
      try {
        const raw = await apiFetch(assessmentVersionDetailPath(clientId, versionId), { headers })
        setDetail(normalizeVersionDetail(raw))
      } catch (e) {
        setDetailError(e?.message ?? 'Could not load version details')
      } finally {
        setDetailLoading(false)
      }
    },
    [clientId, headers],
  )

  useEffect(() => {
    if (selectedVersionId) loadDetail(selectedVersionId)
  }, [selectedVersionId, loadDetail])

  useEffect(() => {
    if (versions.length >= 2) {
      const sorted = [...versions].sort((a, b) => Number(a.versionNumber) - Number(b.versionNumber))
      setBaselineId(String(sorted[0]?.id ?? ''))
      setCurrentId(String(sorted[sorted.length - 1]?.id ?? ''))
    } else {
      setBaselineId(versions[0] ? String(versions[0].id) : '')
      setCurrentId(versions[1] ? String(versions[1].id) : '')
    }
  }, [versions])

  async function onExportLatestAssessmentPdf() {
    if (!latestVersion?.id || exportingPdf) return
    setExportError('')
    setExportingPdf(true)
    try {
      const raw = await apiFetch(assessmentVersionDetailPath(clientId, latestVersion.id), { headers })
      const assessment = normalizeVersionDetail(raw)
      if (!assessment) {
        throw new Error('Could not load latest assessment version')
      }
      await exportAssessmentPdf(
        buildAdminAssessmentPdfReport({
          clientName: clientLabel,
          assessment,
        }),
      )
    } catch (e) {
      setExportError(e?.message ?? 'Export failed')
    } finally {
      setExportingPdf(false)
    }
  }

  async function runCompare() {
    setCompareError('')
    setCompareRows([])
    if (!baselineId || !currentId || baselineId === currentId) {
      setCompareError('Pick two different versions to compare.')
      return
    }
    setCompareLoading(true)
    try {
      const [rawOld, rawNew] = await Promise.all([
        apiFetch(assessmentVersionDetailPath(clientId, baselineId), { headers }),
        apiFetch(assessmentVersionDetailPath(clientId, currentId), { headers }),
      ])
      const older = normalizeVersionDetail(rawOld)
      const newer = normalizeVersionDetail(rawNew)
      const rows = computeVersionDiff(older, newer)
      setCompareRows(rows)
    } catch (e) {
      setCompareError(e?.message ?? 'Compare failed')
    } finally {
      setCompareLoading(false)
    }
  }

  function clearCompareSelection() {
    setCompareRows([])
    setCompareError('')
  }

  function resetCompareSelection() {
    clearCompareSelection()
    if (versions.length >= 2) {
      const sorted = [...versions].sort((a, b) => Number(a.versionNumber) - Number(b.versionNumber))
      setBaselineId(String(sorted[0]?.id ?? ''))
      setCurrentId(String(sorted[sorted.length - 1]?.id ?? ''))
    } else {
      setBaselineId(versions[0] ? String(versions[0].id) : '')
      setCurrentId(versions[1] ? String(versions[1].id) : '')
    }
  }

  function selectVersion(versionId) {
    setSelectedVersionId(versionId)
  }

  function renderStatusBadges(version) {
    const label = assessmentStatusLabel(version.status)
    const isSubmitted = String(version.status ?? '').toUpperCase() === 'SUBMITTED'
    return (
      <div className="verStatusStack">
        <span className={statusBadgeClass(version.status)}>{label}</span>
        {version.isLatest && isSubmitted ? (
          <span className="verBadge verBadgeLatest">Latest Submission</span>
        ) : null}
      </div>
    )
  }

  return (
    <div className="verOverlayBackdrop" role="presentation" onClick={onClose}>
      <div
        ref={dialogRef}
        className="verOverlayPanel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="verOverlayHeader">
          <div className="verOverlayHeading">
            <span className="verOverlayIconWrap" aria-hidden="true">
              <History size={20} strokeWidth={2.25} />
            </span>
            <div className="verOverlayHeadingText">
              <h2 id={titleId} className="verOverlayTitle">
                Assessment Versions
              </h2>
              <p className="verOverlaySubtitle">
                {clientLabel || 'Client'}
                <span className="verOverlaySubtitleSep">·</span>
                Client #{clientId}
              </p>
            </div>
          </div>

          <div className="verOverlayHeaderActions">
            {canExportAssessmentPdf ? (
              <button
                type="button"
                className="verExportBtn"
                disabled={exportingPdf}
                onClick={onExportLatestAssessmentPdf}
              >
                {exportingPdf ? 'Exporting…' : 'Export Assessment Report'}
              </button>
            ) : null}
            <button
              ref={closeBtnRef}
              type="button"
              className="verCloseBtn"
              onClick={onClose}
              aria-label="Close"
            >
              <X size={18} strokeWidth={2.25} aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="verOverlayScroll">
          {exportError ? <div className="alert alertError verOverlayAlert">{exportError}</div> : null}

          {loadError ? (
            <div className="alert alertError verOverlayAlert">
              {loadError}
              <div className="tinyNote verOverlayHint">
                Expected: GET <span className="monoCell">{assessmentVersionsListPath(clientId)}</span>
              </div>
            </div>
          ) : null}

          {loadingList ? (
            <div className="verEmptyState">
              <p className="verEmptyTitle">Loading versions…</p>
              <p className="verEmptyText">Fetching assessment history for this client.</p>
            </div>
          ) : null}

          {!loadingList && versions.length === 0 && !loadError ? (
            <div className="verEmptyState">
              <p className="verEmptyTitle">No versions available</p>
              <p className="verEmptyText">No assessment versions were returned for this client.</p>
            </div>
          ) : null}

          {!loadingList && versions.length > 0 ? (
            <div className="verOverlayBody">
              <section className="verCard">
                <div className="verCardHeader">
                  <h3 className="verCardTitle">
                    <Layers3 size={16} aria-hidden="true" />
                    <span>Version History</span>
                  </h3>
                </div>

                <div className="verTableScroll">
                  <table className="verDataTable">
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Created</th>
                        <th>Framework</th>
                        <th>Overall Score</th>
                        <th>Average Score</th>
                        <th>Status</th>
                        <th aria-label="Actions" />
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => {
                        const selected = String(v.id) === String(selectedVersionId)
                        const created = formatDateParts(v.createdAt)
                        return (
                          <tr
                            key={String(v.id)}
                            className={selected ? 'verRowSelected' : undefined}
                            onClick={() => selectVersion(v.id)}
                          >
                            <td>
                              <div className="verVersionMain">
                                <strong>Version {v.versionNumber}</strong>
                                {v.versionComment ? (
                                  <span className="verVersionComment">{v.versionComment}</span>
                                ) : null}
                              </div>
                            </td>
                            <td>
                              <div className="verDateStack">
                                <span className="verDatePrimary">{created.date}</span>
                                {created.time ? <span className="verDateSecondary">{created.time}</span> : null}
                              </div>
                            </td>
                            <td>
                              <FrameworkCell rows={v.frameworkStatus} />
                            </td>
                            <td>
                              <ScoreCell value={v.globalScore} />
                            </td>
                            <td>
                              <ScoreCell value={v.globalAverageScore} />
                            </td>
                            <td>{renderStatusBadges(v)}</td>
                            <td className="verActionsCell">
                              <button
                                type="button"
                                className={selected ? 'verViewBtn verViewBtnActive' : 'verViewBtn'}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  selectVersion(v.id)
                                }}
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="verMobileList">
                  {versions.map((v) => {
                    const selected = String(v.id) === String(selectedVersionId)
                    const created = formatDateParts(v.createdAt)
                    return (
                      <article
                        key={`m-${v.id}`}
                        className={selected ? 'verMobileCard verMobileCardSelected' : 'verMobileCard'}
                      >
                        <div className="verMobileCardTop">
                          <div>
                            <strong>Version {v.versionNumber}</strong>
                            {v.versionComment ? (
                              <div className="verVersionComment">{v.versionComment}</div>
                            ) : null}
                          </div>
                          {renderStatusBadges(v)}
                        </div>
                        <div className="verMobileMeta">
                          <div>
                            <span className="verMobileLabel">Created</span>
                            <span className="verDatePrimary">{created.date}</span>
                            {created.time ? <span className="verDateSecondary">{created.time}</span> : null}
                          </div>
                          <div>
                            <span className="verMobileLabel">Framework</span>
                            <FrameworkCell rows={v.frameworkStatus} />
                          </div>
                          <div>
                            <span className="verMobileLabel">Overall Score</span>
                            <ScoreCell value={v.globalScore} />
                          </div>
                          <div>
                            <span className="verMobileLabel">Average Score</span>
                            <ScoreCell value={v.globalAverageScore} />
                          </div>
                        </div>
                        <button
                          type="button"
                          className={selected ? 'verViewBtn verViewBtnActive' : 'verViewBtn'}
                          onClick={() => selectVersion(v.id)}
                        >
                          View Details
                        </button>
                      </article>
                    )
                  })}
                </div>
              </section>

              <section className="verCard">
                <div className="verCardHeader">
                  <h3 className="verCardTitle">Version Details</h3>
                  {selectedVersionId ? (
                    <span className="verCardMeta monoCell">ID: {selectedVersionId}</span>
                  ) : null}
                </div>

                {!selectedVersionId ? (
                  <div className="verEmptyState verEmptyStateCompact">
                    <p className="verEmptyTitle">No version selected</p>
                    <p className="verEmptyText">Select a version above to view its details.</p>
                  </div>
                ) : null}

                {detailLoading ? (
                  <div className="verEmptyState verEmptyStateCompact">
                    <p className="verEmptyTitle">Loading details…</p>
                  </div>
                ) : null}

                {detailError ? <div className="alert alertError">{detailError}</div> : null}

                {detail && !detailLoading ? (
                  <div className="verDetailStack">
                    <div className="verSummaryCards">
                      <div className="verSummaryCard">
                        <div className="verSummaryLabel">Overall Score</div>
                        <div className="verSummaryValue">
                          <ScoreCell value={detail.globalScore} />
                        </div>
                        {detail.globalMaturityLabel ? (
                          <div className="tinyNote">{maturityLabelEn(detail.globalMaturityLabel)}</div>
                        ) : null}
                      </div>
                      <div className="verSummaryCard">
                        <div className="verSummaryLabel">Average Score</div>
                        <div className="verSummaryValue">
                          <ScoreCell value={detail.globalAverageScore} />
                        </div>
                      </div>
                      <div className="verSummaryCard">
                        <div className="verSummaryLabel">Status</div>
                        <div className="verSummaryValue">
                          <span className={statusBadgeClass(detail.globalStatus ?? detail.status)}>
                            {assessmentStatusLabel(detail.globalStatus ?? detail.status)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {(detail.frameworkStatus ?? []).length > 0 ? (
                      <div className="verSummaryCards">
                        {(detail.frameworkStatus ?? []).map((item) => (
                          <div key={item.frameworkCode} className="verSummaryCard">
                            <div className="verSummaryLabel">{item.frameworkCode}</div>
                            <div className="verSummaryValue">
                              <span className={statusBadgeClass(item.frameworkStatus)}>
                                {frameworkStatusLabel(item)}
                              </span>
                            </div>
                            <div className="tinyNote">
                              {item.answeredQuestions}/{item.totalQuestions} questions
                              {item.frameworkScore != null ? ` · Overall Score ${item.frameworkScore} / 5` : ''}
                              {item.frameworkAverageScore != null
                                ? ` · Average Score ${item.frameworkAverageScore} / 5`
                                : ''}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    <AssessmentDetailsDomains
                      segments={detail.segments ?? []}
                      assessmentId={detail.id}
                      token={token}
                      onError={setDetailError}
                    />
                  </div>
                ) : null}
              </section>

              <section className="verCard">
                <div className="verCardHeader">
                  <h3 className="verCardTitle">
                    <GitCompareArrows size={16} aria-hidden="true" />
                    <span>Compare Versions</span>
                  </h3>
                </div>

                <p className="verCompareHint">
                  Select a previous and a current version, then run compare.
                </p>

                <div className="verCompareForm">
                  <label className="verCompareField">
                    <span className="verCompareLabel">Previous version</span>
                    <select
                      className="verCompareSelect"
                      value={baselineId}
                      onChange={(e) => setBaselineId(e.target.value)}
                      aria-label="Select previous version"
                    >
                      {versions.map((v) => (
                        <option key={`b-${v.id}`} value={String(v.id)}>
                          Version {v.versionNumber} — {formatDate(v.createdAt)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="verCompareField">
                    <span className="verCompareLabel">Current version</span>
                    <select
                      className="verCompareSelect"
                      value={currentId}
                      onChange={(e) => setCurrentId(e.target.value)}
                      aria-label="Select current version"
                    >
                      {versions.map((v) => (
                        <option key={`c-${v.id}`} value={String(v.id)}>
                          Version {v.versionNumber} — {formatDate(v.createdAt)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="verCompareActions">
                    <button
                      type="button"
                      className="verSecondaryBtn"
                      onClick={clearCompareSelection}
                      disabled={compareLoading || compareRows.length === 0}
                    >
                      Clear Selection
                    </button>
                    <button
                      type="button"
                      className="verSecondaryBtn"
                      onClick={resetCompareSelection}
                      disabled={compareLoading}
                    >
                      Reset
                    </button>
                    <button
                      type="button"
                      className="verPrimaryBtn"
                      disabled={compareLoading}
                      onClick={runCompare}
                    >
                      {compareLoading ? 'Comparing…' : 'Compare'}
                    </button>
                  </div>
                </div>

                {compareError ? <div className="alert alertError">{compareError}</div> : null}

                {compareRows.length > 0 ? (
                  <div className="verCompareResults">
                    <h4 className="verSectionTitleSm">Changes from previous version</h4>
                    <div className="verTableScroll">
                      <table className="verDataTable">
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Domain / question</th>
                            <th>Old score</th>
                            <th>New score</th>
                            <th>Old evidence</th>
                            <th>New evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {compareRows.map((row) => (
                            <tr key={row.key}>
                              <td>
                                <span className={changeBadgeClass(row.type)}>{row.type}</span>
                              </td>
                              <td>
                                <div className="tinyNote monoCell">{row.questionCode}</div>
                                <div>{row.questionText || row.domainLabel}</div>
                                <div className="tinyNote muted">{row.domainLabel}</div>
                                {row.changeReasons?.length ? (
                                  <div className="tinyNote muted">Changed: {row.changeReasons.join(', ')}</div>
                                ) : null}
                              </td>
                              <td>
                                <ScoreCell value={row.oldScore} />
                              </td>
                              <td>
                                <ScoreCell value={row.newScore} />
                              </td>
                              <td className="monoCell tinyNote">{row.oldEvidence}</td>
                              <td className="monoCell tinyNote">{row.newEvidence}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
