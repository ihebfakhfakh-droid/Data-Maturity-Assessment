import { Navigate, useParams } from 'react-router-dom'
import { useAuth } from '../../auth/AuthProvider.jsx'
import { homePathForRole, roleFromAuth } from '../../auth/roles.js'
import { ClientHomePage } from '../client/ClientHomePage.jsx'

export function StaffAssessmentEditPage() {
  const { assessmentId } = useParams()
  const auth = useAuth()
  const role = roleFromAuth(auth)

  if (!assessmentId) {
    return <Navigate to={homePathForRole(role)} replace />
  }

  return <ClientHomePage staffMode staffAssessmentId={assessmentId} />
}
