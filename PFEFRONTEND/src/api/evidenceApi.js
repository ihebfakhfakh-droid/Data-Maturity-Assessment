import { apiFetch } from './client.js'

/**
 * Delete a stored evidence via Spring Boot.
 * Staff uses /api/admin; client uses /api/client.
 */
export async function deleteEvidence(evidenceId, token, { staff = false } = {}) {
  const base = staff ? '/api/admin' : '/api/client'
  await apiFetch(`${base}/evidences/${evidenceId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
}
