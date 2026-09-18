import { apiFetch, apiFetchBlob } from '../api/client.js'

export function saveRecommendationTarget(assessmentId, targetScore, token) {
  return apiFetch(`/api/admin/assessments/${assessmentId}/recommendation-target`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ targetScore }),
  })
}

export async function downloadRecommendationReport(assessmentId, token) {
  const { blob } = await apiFetchBlob(
    `/api/admin/assessments/${assessmentId}/recommendation-report`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/pdf, application/json, application/problem+json',
      },
    },
  )

  const objectUrl = URL.createObjectURL(blob)
  try {
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = 'recommendations-report.pdf'
    document.body.appendChild(link)
    link.click()
    link.remove()
  } finally {
    URL.revokeObjectURL(objectUrl)
  }

  return 'recommendations-report.pdf'
}

export function resolveNdiGlobalScore(assessment) {
  const frameworks = Array.isArray(assessment?.frameworkStatus) ? assessment.frameworkStatus : []
  const ndi = frameworks.find((item) => String(item?.frameworkCode ?? '').toUpperCase() === 'NDI')
  if (ndi?.frameworkScore != null && Number.isFinite(Number(ndi.frameworkScore))) {
    return Number(ndi.frameworkScore)
  }
  const global = assessment?.globalScore ?? assessment?.score
  return global != null && Number.isFinite(Number(global)) ? Number(global) : null
}

export function assessmentHasNdiFramework(assessment) {
  const frameworks = Array.isArray(assessment?.frameworkStatus) ? assessment.frameworkStatus : []
  if (frameworks.some((item) => String(item?.frameworkCode ?? '').toUpperCase() === 'NDI')) {
    return true
  }
  const segments = Array.isArray(assessment?.segments) ? assessment.segments : []
  return segments.some((segment) => String(segment?.segmentCode ?? segment?.id ?? '').toLowerCase().startsWith('ndi_'))
}

export function validateRecommendationTarget(rawValue, currentScore, maxScore = 5) {
  if (rawValue === '' || rawValue == null) {
    return { ok: false, message: 'Target score is required.' }
  }
  const value = Number(rawValue)
  if (!Number.isFinite(value)) {
    return { ok: false, message: 'Target score must be a number.' }
  }
  if (value < 0) {
    return { ok: false, message: 'Target score cannot be negative.' }
  }
  if (currentScore == null || !Number.isFinite(currentScore)) {
    return { ok: false, message: 'Current score is unavailable.' }
  }
  if (value <= currentScore) {
    return {
      ok: false,
      message: 'Target score must be greater than the current score.',
    }
  }
  if (value > maxScore) {
    return {
      ok: false,
      message: `Target score must not exceed ${maxScore}.`,
    }
  }
  return { ok: true, value }
}
