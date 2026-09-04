import { useEffect, useId, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, FileText, Loader2, Paperclip, Trash2, X } from 'lucide-react'

function formatSize(bytes) {
  const n = Number(bytes)
  if (!Number.isFinite(n) || n <= 0) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function isStoredEvidenceId(id) {
  return id != null && !String(id).startsWith('pending-') && Number.isFinite(Number(id))
}

/**
 * Collapsible evidence list with optional delete (confirmation modal).
 * Each instance keeps its own open/closed state (per question).
 */
export function EvidenceFilesPanel({
  items = [],
  canDelete = false,
  deletingId = null,
  onRequestDelete,
  emptyLabel = 'No evidence',
  answerId = null,
}) {
  const reactId = useId()
  const listDomId = `evidence-list-${answerId ?? reactId.replace(/:/g, '')}`
  const list = Array.isArray(items) ? items.filter((item) => item?.id != null) : []
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (list.length === 0) setExpanded(false)
  }, [list.length])

  if (list.length === 0) {
    return <div className="evidenceFilesEmpty muted">{emptyLabel}</div>
  }

  return (
    <div className="evidenceFilesPanel">
      <button
        type="button"
        className="evidence-toggle"
        onClick={() => setExpanded((open) => !open)}
        aria-expanded={expanded}
        aria-controls={listDomId}
      >
        <Paperclip size={17} strokeWidth={2.2} aria-hidden="true" />
        <span>Evidences ({list.length})</span>
        {expanded ? (
          <ChevronUp size={17} strokeWidth={2.2} aria-hidden="true" />
        ) : (
          <ChevronDown size={17} strokeWidth={2.2} aria-hidden="true" />
        )}
      </button>

      {expanded ? (
        <ul id={listDomId} className="evidenceFilesList" role="list">
          {list.map((item) => {
            const id = item.id
            const name = item.fileName || `Evidence ${id}`
            const sizeLabel = formatSize(item.sizeBytes ?? item.size)
            const busy = deletingId != null && String(deletingId) === String(id)
            const stored = isStoredEvidenceId(id)
            return (
              <li key={id} className="evidenceFileItem">
                <div className="evidenceFileMeta" title={name}>
                  <FileText size={16} strokeWidth={2.2} className="evidenceFileIcon" aria-hidden="true" />
                  <div className="evidenceFileText">
                    <span className="evidenceFileName">{name}</span>
                    {sizeLabel ? <span className="evidenceFileSize">{sizeLabel}</span> : null}
                  </div>
                </div>
                {canDelete && stored && typeof onRequestDelete === 'function' ? (
                  <button
                    type="button"
                    className="evidenceDeleteBtn"
                    disabled={deletingId != null}
                    aria-label={`Delete evidence ${name}`}
                    onClick={() => onRequestDelete(item)}
                  >
                    {busy ? (
                      <Loader2 size={15} strokeWidth={2.4} className="evidenceDeleteSpinner" aria-hidden="true" />
                    ) : (
                      <Trash2 size={15} strokeWidth={2.2} aria-hidden="true" />
                    )}
                    <span>{busy ? 'Deleting…' : 'Delete'}</span>
                  </button>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}

/**
 * Accessible confirmation dialog for evidence deletion.
 */
export function EvidenceDeleteConfirmModal({
  open,
  fileName = '',
  deleting = false,
  onCancel,
  onConfirm,
}) {
  const titleId = useId()
  const cancelRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const t = window.setTimeout(() => cancelRef.current?.focus(), 0)

    function onKeyDown(event) {
      if (event.key === 'Escape' && !deleting) {
        event.preventDefault()
        onCancel?.()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(t)
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, deleting, onCancel])

  if (!open) return null

  return (
    <div className="staffDialogBackdrop" role="presentation" onClick={() => (!deleting ? onCancel?.() : null)}>
      <div
        className="staffDialogPanel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="staffDialogHeader">
          <div className="staffDialogHeading">
            <div className="staffDialogIconWrap" aria-hidden="true">
              <Trash2 size={20} strokeWidth={2.25} />
            </div>
            <div>
              <h2 id={titleId} className="staffDialogTitle">
                Delete Evidence
              </h2>
              <p className="staffDialogSubtitle">This action cannot be undone.</p>
            </div>
          </div>
          <button
            type="button"
            className="staffDialogClose"
            aria-label="Close"
            disabled={deleting}
            onClick={() => onCancel?.()}
          >
            <X size={18} strokeWidth={2.25} aria-hidden="true" />
          </button>
        </div>
        <div className="staffDialogBody">
          <p className="staffDialogSubtitle" style={{ margin: 0 }}>
            Are you sure you want to delete “{fileName}”? This action cannot be undone.
          </p>
          <div className="staffDialogActions">
            <button
              ref={cancelRef}
              type="button"
              className="btn btnGhost"
              disabled={deleting}
              onClick={() => onCancel?.()}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btnDanger btnWithIcon"
              disabled={deleting}
              onClick={() => onConfirm?.()}
            >
              {deleting ? (
                <Loader2 size={16} strokeWidth={2.4} className="evidenceDeleteSpinner" aria-hidden="true" />
              ) : (
                <Trash2 size={16} strokeWidth={2.2} aria-hidden="true" />
              )}
              <span>{deleting ? 'Deleting…' : 'Delete Evidence'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
