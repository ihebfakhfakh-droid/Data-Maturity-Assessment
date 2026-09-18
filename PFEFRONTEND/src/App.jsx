import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { ClientHomePage } from './pages/client/ClientHomePage.jsx'
import { AdminDashboardPage } from './pages/admin/AdminDashboardPage.jsx'
import { StaffAssessmentEditPage } from './pages/admin/StaffAssessmentEditPage.jsx'
import { RequireAuth } from './routes/RequireAuth.jsx'
import { RequireRole } from './routes/RequireRole.jsx'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<Navigate to="/login" replace />} />

        <Route element={<RequireAuth />}>
          <Route
            path="/client"
            element={
              <RequireRole roles={['CLIENT']}>
                <ClientHomePage />
              </RequireRole>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireRole roles={['ADMIN']}>
                <AdminDashboardPage />
              </RequireRole>
            }
          />
          <Route
            path="/manager"
            element={
              <RequireRole roles={['MANAGER']}>
                <AdminDashboardPage />
              </RequireRole>
            }
          />
          <Route
            path="/consultant"
            element={
              <RequireRole roles={['CONSULTANT']}>
                <AdminDashboardPage />
              </RequireRole>
            }
          />
          <Route
            path="/admin/assessments/:assessmentId/edit"
            element={
              <RequireRole roles={['ADMIN']}>
                <StaffAssessmentEditPage />
              </RequireRole>
            }
          />
          <Route
            path="/manager/assessments/:assessmentId/edit"
            element={
              <RequireRole roles={['MANAGER']}>
                <StaffAssessmentEditPage />
              </RequireRole>
            }
          />
          <Route
            path="/consultant/assessments/:assessmentId/edit"
            element={
              <RequireRole roles={['CONSULTANT']}>
                <StaffAssessmentEditPage />
              </RequireRole>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
