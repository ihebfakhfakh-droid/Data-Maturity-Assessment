import { apiFetchBlob } from './client.js'

/**
 * Generate Acceptance Criteria PDF for an evidence via Spring Boot.
 * Downloads automatically; React never calls the Python microservice.
 */
export async function downloadAcceptanceCriteriaReport(evidenceId, token) {
  const { blob, filename } = await apiFetchBlob(
    `/api/staff/evidences/${evidenceId}/acceptance-criteria-report`,
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
    link.download = filename || `acceptance-criteria-evidence-${evidenceId}.pdf`
    document.body.appendChild(link)
    link.click()
    link.remove()
  } finally {
    URL.revokeObjectURL(objectUrl)
  }

  return filename
}
