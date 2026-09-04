import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Crosshair, Loader2, Sparkles, X } from 'lucide-react'
import {
  assessmentHasNdiFramework,
  downloadRecommendationReport,
  resolveNdiGlobalScore,
  saveRecommendationTarget,
  validateRecommendationTarget,
} from '../../api/recommendationApi.js'

const MAX_SCORE = 5

/**
 * AI recommendation actions for CONSULTANT / MANAGER on a SUBMITTED NDI assessment.
 * Button labels depend on whether assessment.recommendationTargetScore is already persisted.
 */
export function RecommendationActionsPanel({
  assessment,
  token,
  canUseRecommendations,
  onTargetSaved,
  onError,
  onSuccess,
}) {
  const [modalOpen, setModalOpen] = useState(false)
  const [targetInput, setTargetInput] = useState('')
  const [modalError, setModalError] = useState('')
  const [savingTarget, setSavingTarget] = useState(false)
  const [generating, setGenerating] = useState(false)

  const titleId = useId()
  const inputId = useId()
  const hintId = useId()
  const errorId = useId()
  const inputRef = useRef(null)
  const dialogRef = useRef(null)

  const currentScore = useMemo(() => resolveNdiGlobalScore(assessment), [assessment])
  const savedTarget = assessment?.recommendationTargetScore
  const hasSavedTarget = savedTarget != null && Number.isFinite(Number(savedTarget))
  const isNdi = assessmentHasNdiFramework(assessment)
  const assessmentId = assessment?.id

  useEffect(() => {
    if (!modalOpen) return undefined

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusTimer = window.setTimeout(() => {
      inputRef.current?.focus()
    }, 0)

    function onKeyDown(event) {
      if (event.key === 'Escape' && !savingTarget) {
        event.preventDefault()
        setModalOpen(false)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(focusTimer)
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [modalOpen, savingTarget])

  if (!canUseRecommendations || !assessmentId) {
    return null
  }

  if (!isNdi) {
    return (
      <div className="alert alertInfo aiTargetPageAlert">
        AI recommendation generation is not yet available for this framework.
      </div>
    )
  }

  async function onSaveTarget(event) {
    event.preventDefault()
    setModalError('')
    const validation = validateRecommendationTarget(targetInput, currentScore, MAX_SCORE)
    if (!validation.ok) {
      setModalError(validation.message)
      return
    }

    setSavingTarget(true)
    try {
      const response = await saveRecommendationTarget(assessmentId, validation.value, token)
      onTargetSaved?.(response)
      setModalOpen(false)
      onSuccess?.('AI target saved successfully.')
    } catch (error) {
      const message = String(error?.message ?? 'Unable to save the AI target.')
      setModalError(message)
      onError?.(message)
    } finally {
      setSavingTarget(false)
    }
  }

  async function onGenerateReport() {
    if (!hasSavedTarget || generating) return
    setGenerating(true)
    onError?.('')
    try {
      await downloadRecommendationReport(assessmentId, token)
      onSuccess?.('PDF report downloaded.')
    } catch (error) {
      onError?.(String(error?.message ?? 'PDF report generation failed.'))
    } finally {
      setGenerating(false)
    }
  }

  function openModal() {
    setModalError('')
    setTargetInput(hasSavedTarget ? String(savedTarget) : '')
    setModalOpen(true)
  }

  function closeModal() {
    if (savingTarget) return
    setModalOpen(false)
  }

  const modalTitle = hasSavedTarget ? 'Edit AI Target' : 'Define AI Target'
  const modalSubtitle = hasSavedTarget
    ? 'Update the maturity level you want to achieve.'
    : 'Set the maturity level you want to achieve.'

  return (
    <>
      <div className="aiTargetActions">
        {hasSavedTarget ? (
          <span className="aiTargetBadge">
            AI Target: <strong>{Number(savedTarget)}</strong> / {MAX_SCORE}
          </span>
        ) : null}
        <button
          type="button"
          className="btn btnGhost btnSm"
          onClick={openModal}
          disabled={generating || savingTarget || currentScore == null}
        >
          {hasSavedTarget ? 'Edit Target' : 'Define Target'}
        </button>
        <button
          type="button"
          className="btn btnPrimary btnSm btnWithIcon aiGeneratePdfBtn"
          onClick={onGenerateReport}
          disabled={!hasSavedTarget || generating || savingTarget}
          title={!hasSavedTarget ? 'Define a valid AI target first.' : undefined}
          aria-label="Generate AI recommendations PDF"
          aria-busy={generating}
        >
          {generating ? (
            <Loader2 size={18} className="btnIcon aiGeneratePdfSpinner" aria-hidden="true" />
          ) : (
            <Sparkles size={18} className="btnIcon" aria-hidden="true" />
          )}
          <span>
            {generating ? 'Generating AI Recommendations...' : 'Generate AI Recommendations PDF'}
          </span>
        </button>
      </div>

      {generating ? (
        <div className="alert alertInfo aiTargetPageAlert" role="status">
          Generating AI Recommendations...
        </div>
      ) : null}

      {modalOpen ? (
        <div
          className="aiTargetOverlay"
          role="presentation"
          onClick={closeModal}
        >
          <div
            ref={dialogRef}
            className="aiTargetDialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="aiTargetDialogHeader">
              <div className="aiTargetDialogHeading">
                <span className="aiTargetIconWrap" aria-hidden="true">
                  <Crosshair size={20} strokeWidth={2.25} />
                </span>
                <div>
                  <h3 id={titleId} className="aiTargetDialogTitle">
                    {modalTitle}
                  </h3>
                  <p className="aiTargetDialogSubtitle">{modalSubtitle}</p>
                </div>
              </div>
              <button
                type="button"
                className="aiTargetCloseBtn"
                onClick={closeModal}
                disabled={savingTarget}
                aria-label="Close"
              >
                <X size={18} strokeWidth={2.25} aria-hidden="true" />
              </button>
            </div>

            <div className="aiTargetCurrentCard">
              <div className="aiTargetCurrentMeta">
                <span className="aiTargetCurrentLabel">Current Score</span>
                <span className="aiTargetFrameworkBadge">NDI</span>
              </div>
              <div className="aiTargetCurrentValue">
                <strong>{currentScore ?? '—'}</strong>
                <span> / {MAX_SCORE}</span>
              </div>
            </div>

            <form className="aiTargetForm" onSubmit={onSaveTarget}>
              <label className="aiTargetFieldLabel" htmlFor={inputId}>
                New Target
              </label>
              <div className="aiTargetInputWrap">
                <input
                  ref={inputRef}
                  id={inputId}
                  className="aiTargetInput"
                  type="number"
                  inputMode="decimal"
                  step="0.01"
                  min={currentScore != null ? currentScore + 0.01 : 0}
                  max={MAX_SCORE}
                  value={targetInput}
                  onChange={(event) => setTargetInput(event.target.value)}
                  disabled={savingTarget}
                  required
                  aria-describedby={modalError ? `${hintId} ${errorId}` : hintId}
                  aria-invalid={Boolean(modalError)}
                />
                <span className="aiTargetInputSuffix" aria-hidden="true">
                  / {MAX_SCORE}
                </span>
              </div>
              <p id={hintId} className="aiTargetHint">
                Allowed value: greater than {currentScore ?? '—'} and less than or equal to {MAX_SCORE}.
              </p>
              {modalError ? (
                <div id={errorId} className="aiTargetError" role="alert">
                  {modalError}
                </div>
              ) : null}

              <div className="aiTargetActionsRow">
                <button
                  type="button"
                  className="aiTargetCancelBtn"
                  onClick={closeModal}
                  disabled={savingTarget}
                >
                  Cancel
                </button>
                <button type="submit" className="aiTargetSaveBtn" disabled={savingTarget}>
                  {savingTarget ? 'Saving...' : 'Save Target'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  )
}
