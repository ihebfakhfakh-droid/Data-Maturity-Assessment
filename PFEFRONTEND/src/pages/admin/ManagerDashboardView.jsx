import {
  ClipboardList,
  FolderKanban,
  Layers3,
  UserCircle,
  Users,
  UsersRound,
} from 'lucide-react'
import { SectionHeading } from '../../ui/IconBox.jsx'
import { extractAssignedFrameworks, formatClientLabel } from './frameworkUtils.js'

function assessmentStatusValue(item) {
  return String(item?.globalStatus ?? item?.status ?? item?.workflowStatus ?? '').toUpperCase()
}

function assessmentStatusLabel(item) {
  const status = assessmentStatusValue(item)
  if (status === 'SUBMITTED') return 'Submitted'
  if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'Current Assessment'
  return status || '—'
}

function statusBadgeClass(item) {
  const status = assessmentStatusValue(item)
  if (status === 'SUBMITTED') return 'proBadge proBadgeSubmitted'
  if (status === 'DRAFT' || status === 'IN_PROGRESS') return 'proBadge proBadgeCurrent'
  return 'proBadge proBadgeNeutral'
}

function frameworkProgress(item) {
  const rows = Array.isArray(item?.frameworkStatus) ? item.frameworkStatus : []
  if (rows.length === 0) return null
  const answered = rows.reduce((sum, row) => sum + Number(row?.answeredQuestions ?? 0), 0)
  const total = rows.reduce((sum, row) => sum + Number(row?.totalQuestions ?? 0), 0)
  if (!total || total <= 0) return null
  return { answered, total, percent: Math.min(100, Math.round((answered / total) * 100)) }
}

function frameworksLabel(item) {
  const rows = Array.isArray(item?.frameworkStatus) ? item.frameworkStatus : []
  if (rows.length > 0) {
    return rows.map((row) => row.frameworkCode ?? row.code ?? 'Framework').join(', ')
  }
  const frameworks = item?.frameworks ?? item?.frameworkTags ?? []
  return Array.isArray(frameworks) && frameworks.length > 0 ? frameworks.join(', ') : '—'
}

function projectName(project, client) {
  return (
    project?.name ??
    project?.projectName ??
    project?.title ??
    `Project ${project?.id ?? project?.projectId ?? client?.id ?? ''}`
  )
}

function overallScore(item) {
  const value = item?.globalScore ?? item?.score ?? item?.frameworkScore
  return value === null || value === undefined || value === '' ? null : value
}

function averageScore(item) {
  const value = item?.globalAverageScore ?? item?.frameworkAverageScore ?? item?.averageScore
  return value === null || value === undefined || value === '' ? null : value
}

function formatScore(value) {
  if (value === null || value === undefined || value === '') return '—'
  const num = Number(value)
  if (Number.isFinite(num)) return Number.isInteger(num) ? String(num) : num.toFixed(1)
  return String(value)
}

function submissionDate(item) {
  const raw =
    item?.submittedAt ??
    item?.submissionDate ??
    item?.submittedDate ??
    item?.completedAt ??
    item?.updatedAt ??
    item?.createdAt
  if (!raw) return '—'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return String(raw)
  return date.toLocaleDateString()
}

function ProgressBar({ answered, total, percent }) {
  return (
    <div className="mgrProgress" title={`${answered} / ${total} questions`}>
      <div className="mgrProgressTrack" aria-hidden="true">
        <div className="mgrProgressFill" style={{ width: `${percent}%` }} />
      </div>
      <span className="mgrProgressLabel">
        {answered}/{total}
      </span>
    </div>
  )
}

function AssessmentInfoTable({ rows, loading, emptyLabel, showSubmissionDate = false }) {
  return (
    <>
      <div className="proTableWrap proTableDesktopOnly mgrAssessmentsTableWrap">
        <table
          className={`proTable mgrDashTable mgrAssessmentsTable${showSubmissionDate ? ' mgrAssessmentsTableWithDate' : ''}`}
        >
          <thead>
            <tr>
              <th>Client</th>
              <th>Framework</th>
              <th>Progress</th>
              <th>Overall Score</th>
              <th>Average Score</th>
              <th>Status</th>
              {showSubmissionDate ? <th>Submission Date</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const client = row.client
              const progress = frameworkProgress(row)
              return (
                <tr key={`a-${row.id}-${client?.id ?? 'x'}`}>
                  <td>
                    <strong>{client?.fullName ?? row.clientName ?? client?.email ?? '—'}</strong>
                    <div className="tinyNote">{client?.email ?? row.clientEmail ?? ''}</div>
                  </td>
                  <td>{frameworksLabel(row)}</td>
                  <td>
                    {progress ? (
                      <ProgressBar answered={progress.answered} total={progress.total} percent={progress.percent} />
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{formatScore(overallScore(row))}</td>
                  <td>{formatScore(averageScore(row))}</td>
                  <td className="mgrStatusCell">
                    <span className={`${statusBadgeClass(row)} mgrStatusBadge`}>{assessmentStatusLabel(row)}</span>
                  </td>
                  {showSubmissionDate ? <td>{submissionDate(row)}</td> : null}
                </tr>
              )
            })}
          </tbody>
        </table>
        {!loading && rows.length === 0 ? <div className="proEmptyState">{emptyLabel}</div> : null}
      </div>

      <div className="proMobileList">
        {rows.length === 0 ? (
          <div className="proEmptyState">{emptyLabel}</div>
        ) : (
          rows.map((row) => {
            const client = row.client
            const progress = frameworkProgress(row)
            return (
              <article key={`am-${row.id}-${client?.id ?? 'x'}`} className="proMobileCard">
                <div>
                  <strong>{client?.fullName ?? row.clientName ?? client?.email ?? '—'}</strong>
                  <div className="tinyNote">{client?.email ?? ''}</div>
                </div>
                <div>
                  <span className="proMobileLabel">Framework</span>
                  {frameworksLabel(row)}
                </div>
                {progress ? (
                  <div>
                    <span className="proMobileLabel">Progress</span>
                    <ProgressBar answered={progress.answered} total={progress.total} percent={progress.percent} />
                  </div>
                ) : null}
                <div>
                  <span className="proMobileLabel">Overall Score</span>
                  {formatScore(overallScore(row))}
                </div>
                <div>
                  <span className="proMobileLabel">Average Score</span>
                  {formatScore(averageScore(row))}
                </div>
                <div>
                  <span className="proMobileLabel">Status</span>
                  <span className={statusBadgeClass(row)}>{assessmentStatusLabel(row)}</span>
                </div>
                {showSubmissionDate ? (
                  <div>
                    <span className="proMobileLabel">Submission Date</span>
                    {submissionDate(row)}
                  </div>
                ) : null}
              </article>
            )
          })
        )}
      </div>
    </>
  )
}

/**
 * Consultation-only staff dashboard (no action buttons / no Actions column).
 * Used by MANAGER and ADMIN. CONSULTANT has no dedicated Dashboard tab.
 */
export function ManagerDashboardView({
  loading = false,
  role = 'MANAGER',
  stats,
  clientCount = 0,
  assessments = [],
  consultants = [],
  managers = [],
  projects = [],
  frameworks = [],
}) {
  const isAdmin = role === 'ADMIN'

  const currentAssessments = assessments
    .filter((item) => {
      const status = assessmentStatusValue(item)
      return status === 'DRAFT' || status === 'IN_PROGRESS'
    })
    .slice(0, 8)

  const recentSubmitted = assessments
    .filter((item) => assessmentStatusValue(item) === 'SUBMITTED')
    .slice(0, 8)

  const consultantRows = (Array.isArray(consultants) ? consultants : []).slice(0, 8)
  const managerRows = (Array.isArray(managers) ? managers : []).slice(0, 8)
  const projectRows = (Array.isArray(projects) ? projects : []).slice(0, 8)
  const frameworkRows = (Array.isArray(frameworks) ? frameworks : []).slice(0, 12)

  const subtitle = isAdmin
    ? 'Overview of projects, users, frameworks, and assessments across the platform.'
    : 'Overview of your projects, consultants, and current assessments.'

  return (
    <section className="mgrDashboard">
      <div className="mgrDashboardHeader">
        <div>
          <h1 className="mgrDashboardTitle">Dashboard</h1>
          <p className="mgrDashboardSubtitle">{subtitle}</p>
        </div>
        {loading ? <span className="badge dashboardRefreshBadge">Refreshing</span> : null}
      </div>

      <div className={`mgrMetricGrid ${isAdmin ? 'mgrMetricGridAdmin' : ''}`}>
        <div className="mgrMetricCard">
          <span className="mgrMetricIcon" aria-hidden="true">
            <FolderKanban size={20} strokeWidth={2.2} />
          </span>
          <span className="mgrMetricLabel">{isAdmin ? 'Projects' : 'My Projects'}</span>
          <strong className="mgrMetricValue">{stats?.projectCount ?? 0}</strong>
          <span className="mgrMetricHint">Client projects in scope</span>
        </div>

        {isAdmin ? (
          <div className="mgrMetricCard">
            <span className="mgrMetricIcon" aria-hidden="true">
              <Users size={20} strokeWidth={2.2} />
            </span>
            <span className="mgrMetricLabel">Clients</span>
            <strong className="mgrMetricValue">{clientCount}</strong>
            <span className="mgrMetricHint">Registered client accounts</span>
          </div>
        ) : null}

        <div className="mgrMetricCard">
          <span className="mgrMetricIcon" aria-hidden="true">
            <UsersRound size={20} strokeWidth={2.2} />
          </span>
          <span className="mgrMetricLabel">{isAdmin ? 'Consultants' : 'My Consultants'}</span>
          <strong className="mgrMetricValue">{stats?.consultantCount ?? 0}</strong>
          <span className="mgrMetricHint">{isAdmin ? 'Active consultants' : 'Consultants in your team'}</span>
        </div>

        {isAdmin ? (
          <div className="mgrMetricCard">
            <span className="mgrMetricIcon" aria-hidden="true">
              <UserCircle size={20} strokeWidth={2.2} />
            </span>
            <span className="mgrMetricLabel">Managers</span>
            <strong className="mgrMetricValue">{stats?.managerCount ?? 0}</strong>
            <span className="mgrMetricHint">Team management users</span>
          </div>
        ) : null}

        <div className="mgrMetricCard">
          <span className="mgrMetricIcon" aria-hidden="true">
            <ClipboardList size={20} strokeWidth={2.2} />
          </span>
          <span className="mgrMetricLabel">{isAdmin ? 'Assessments' : 'Current Assessments'}</span>
          <strong className="mgrMetricValue">
            {isAdmin ? (stats?.assessmentCount ?? 0) : (stats?.draftAssessmentCount ?? 0)}
          </strong>
          <span className="mgrMetricHint">
            {stats?.draftAssessmentCount ?? 0} current · {stats?.submittedAssessmentCount ?? 0} submitted
          </span>
        </div>

        {isAdmin ? (
          <div className="mgrMetricCard">
            <span className="mgrMetricIcon" aria-hidden="true">
              <Layers3 size={20} strokeWidth={2.2} />
            </span>
            <span className="mgrMetricLabel">Frameworks</span>
            <strong className="mgrMetricValue">{stats?.frameworkCount ?? frameworkRows.length}</strong>
            <span className="mgrMetricHint">Evaluation frameworks available</span>
          </div>
        ) : null}
      </div>

      <article className="mgrDashCard">
        <div className="mgrDashCardHeader">
          <SectionHeading
            icon={ClipboardList}
            title="Current Assessments"
            subtitle="Draft and in-progress assessments in scope."
            badge={stats?.draftAssessmentCount ?? currentAssessments.length}
          />
        </div>
        <AssessmentInfoTable
          rows={currentAssessments}
          loading={loading}
          emptyLabel="No current assessments in your scope."
        />
      </article>

      {isAdmin ? (
        <article className="mgrDashCard">
          <div className="mgrDashCardHeader">
            <SectionHeading
              icon={ClipboardList}
              title="Recent Submitted Assessments"
              subtitle="Latest submitted assessments across clients."
              badge={stats?.submittedAssessmentCount ?? recentSubmitted.length}
            />
          </div>
          <AssessmentInfoTable
            rows={recentSubmitted}
            loading={loading}
            emptyLabel="No submitted assessments yet."
            showSubmissionDate
          />
        </article>
      ) : null}

      <article className="mgrDashCard">
        <div className="mgrDashCardHeader">
          <SectionHeading
            icon={UsersRound}
            title={isAdmin ? 'Consultants' : 'My Consultants'}
            subtitle={isAdmin ? 'Consultants registered on the platform.' : 'Consultants assigned in your management scope.'}
            badge={stats?.consultantCount ?? consultantRows.length}
          />
        </div>

        <div className="proTableWrap proTableDesktopOnly">
          <table className="proTable mgrDashTable">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Managed by</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {consultantRows.map((consultant) => (
                <tr key={`c-${consultant.id}`}>
                  <td>
                    <strong>{consultant.fullName ?? '—'}</strong>
                  </td>
                  <td className="monoCell">{consultant.email ?? '—'}</td>
                  <td>{consultant.managerName ?? '—'}</td>
                  <td>
                    <span className="proBadge proBadgeConsultant">Consultant</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && consultantRows.length === 0 ? (
            <div className="proEmptyState">No consultants found in your scope.</div>
          ) : null}
        </div>

        <div className="proMobileList">
          {consultantRows.length === 0 ? (
            <div className="proEmptyState">No consultants found in your scope.</div>
          ) : (
            consultantRows.map((consultant) => (
              <article key={`cm-${consultant.id}`} className="proMobileCard">
                <div>
                  <strong>{consultant.fullName ?? '—'}</strong>
                  <div className="tinyNote monoCell">{consultant.email ?? ''}</div>
                </div>
                <div>
                  <span className="proMobileLabel">Managed by</span>
                  {consultant.managerName ?? '—'}
                </div>
              </article>
            ))
          )}
        </div>
      </article>

      {isAdmin ? (
        <article className="mgrDashCard">
          <div className="mgrDashCardHeader">
            <SectionHeading
              icon={UserCircle}
              title="Managers"
              subtitle="Managers registered on the platform."
              badge={stats?.managerCount ?? managerRows.length}
            />
          </div>

          <div className="proTableWrap proTableDesktopOnly">
            <table className="proTable mgrDashTable">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {managerRows.map((manager) => (
                  <tr key={`m-${manager.id}`}>
                    <td>
                      <strong>{manager.fullName ?? '—'}</strong>
                    </td>
                    <td className="monoCell">{manager.email ?? '—'}</td>
                    <td>
                      <span className="proBadge proBadgeManager">Manager</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && managerRows.length === 0 ? (
              <div className="proEmptyState">No managers found.</div>
            ) : null}
          </div>

          <div className="proMobileList">
            {managerRows.length === 0 ? (
              <div className="proEmptyState">No managers found.</div>
            ) : (
              managerRows.map((manager) => (
                <article key={`mm-${manager.id}`} className="proMobileCard">
                  <div>
                    <strong>{manager.fullName ?? '—'}</strong>
                    <div className="tinyNote monoCell">{manager.email ?? ''}</div>
                  </div>
                  <div>
                    <span className="proMobileLabel">Role</span>
                    <span className="proBadge proBadgeManager">Manager</span>
                  </div>
                </article>
              ))
            )}
          </div>
        </article>
      ) : null}

      <article className="mgrDashCard">
        <div className="mgrDashCardHeader">
          <SectionHeading
            icon={FolderKanban}
            title="Existing Projects"
            subtitle="Projects linked to clients in scope."
            badge={stats?.projectCount ?? projectRows.length}
          />
        </div>

        <div className="proTableWrap proTableDesktopOnly">
          <table className="proTable mgrDashTable">
            <thead>
              <tr>
                <th>Project</th>
                <th>Client</th>
                <th>Frameworks</th>
              </tr>
            </thead>
            <tbody>
              {projectRows.map(({ client, project }) => {
                const frameworksAssigned = extractAssignedFrameworks(project)
                const id = project?.id ?? project?.projectId ?? client?.id
                return (
                  <tr key={`p-${client?.id}-${id}`}>
                    <td>
                      <strong>{projectName(project, client)}</strong>
                      <div className="tinyNote">ID: {id ?? '—'}</div>
                    </td>
                    <td>{formatClientLabel(client)}</td>
                    <td>
                      {frameworksAssigned.length > 0
                        ? frameworksAssigned.map((fw) => fw.label ?? fw.value ?? fw.key).join(', ')
                        : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {!loading && projectRows.length === 0 ? (
            <div className="proEmptyState">No existing projects found.</div>
          ) : null}
        </div>

        <div className="proMobileList">
          {projectRows.length === 0 ? (
            <div className="proEmptyState">No existing projects found.</div>
          ) : (
            projectRows.map(({ client, project }) => {
              const frameworksAssigned = extractAssignedFrameworks(project)
              const id = project?.id ?? project?.projectId ?? client?.id
              return (
                <article key={`pm-${client?.id}-${id}`} className="proMobileCard">
                  <div>
                    <strong>{projectName(project, client)}</strong>
                    <div className="tinyNote">{formatClientLabel(client)}</div>
                  </div>
                  <div>
                    <span className="proMobileLabel">Frameworks</span>
                    {frameworksAssigned.length > 0
                      ? frameworksAssigned.map((fw) => fw.label ?? fw.value ?? fw.key).join(', ')
                      : '—'}
                  </div>
                </article>
              )
            })
          )}
        </div>
      </article>

      {isAdmin ? (
        <article className="mgrDashCard">
          <div className="mgrDashCardHeader">
            <SectionHeading
              icon={Layers3}
              title="Frameworks"
              subtitle="Built-in and admin-defined maturity frameworks."
              badge={stats?.frameworkCount ?? frameworkRows.length}
            />
          </div>

          <div className="proTableWrap proTableDesktopOnly">
            <table className="proTable mgrDashTable">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {frameworkRows.map((fw) => {
                  const code = fw.value ?? fw.code ?? fw.key ?? '—'
                  const name = fw.label ?? fw.name ?? code
                  const builtIn = Boolean(fw.builtIn ?? fw.isBuiltIn)
                  return (
                    <tr key={`fw-${code}`}>
                      <td className="monoCell">{code}</td>
                      <td>
                        <strong>{name}</strong>
                      </td>
                      <td>
                        <span className={builtIn ? 'proBadge proBadgeNeutral' : 'proBadge proBadgeCurrent'}>
                          {builtIn ? 'Built-in' : 'Custom'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {!loading && frameworkRows.length === 0 ? (
              <div className="proEmptyState">No frameworks available.</div>
            ) : null}
          </div>

          <div className="proMobileList">
            {frameworkRows.length === 0 ? (
              <div className="proEmptyState">No frameworks available.</div>
            ) : (
              frameworkRows.map((fw) => {
                const code = fw.value ?? fw.code ?? fw.key ?? '—'
                const name = fw.label ?? fw.name ?? code
                const builtIn = Boolean(fw.builtIn ?? fw.isBuiltIn)
                return (
                  <article key={`fwm-${code}`} className="proMobileCard">
                    <div>
                      <strong>{name}</strong>
                      <div className="tinyNote monoCell">{code}</div>
                    </div>
                    <div>
                      <span className="proMobileLabel">Type</span>
                      <span className={builtIn ? 'proBadge proBadgeNeutral' : 'proBadge proBadgeCurrent'}>
                        {builtIn ? 'Built-in' : 'Custom'}
                      </span>
                    </div>
                  </article>
                )
              })
            )}
          </div>
        </article>
      ) : null}
    </section>
  )
}
