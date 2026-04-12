import { useEffect } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, Bell, BriefcaseBusiness, Building, Building2, CalendarDays, ClipboardCheck, Clock3, CreditCard, Fingerprint, GitBranch, Landmark, LayoutDashboard, LogOut, MapPin, PlaneTakeoff, ReceiptText, Repeat, ScrollText, Target, Users, Wrench } from 'lucide-react'
import { SidebarNav, type NavGroup } from './SidebarNav'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { useAuth } from '@/hooks/useAuth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { NotificationBell } from '@/components/ui/NotificationBell'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { getAccessStateTone } from '@/lib/status'
import { OrgSetupBanner } from '@/components/org/OrgSetupBanner'
import { useRefreshCtImpersonation, useStopCtImpersonation } from '@/hooks/useCtOrganisations'
import { formatDateTime } from '@/lib/format'
import { hasAnyPermission, hasPermission } from '@/lib/rbac'
import type { AuthUser } from '@/types/auth'
import { toast } from 'sonner'

function isFeatureEnabled(featureFlags: Record<string, boolean> | undefined, featureCode: string) {
  return featureFlags?.[featureCode] ?? true
}

function buildNavGroups(user: AuthUser | null | undefined): NavGroup[] {
  const featureFlags = user?.feature_flags
  const canReadEmployees = hasPermission(user, 'org.employees.read')
  const canReadPayroll = hasPermission(user, 'org.payroll.read')
  const canReadReports = hasPermission(user, 'org.reports.read')
  const canAccessApprovals = hasAnyPermission(user, ['org.approvals.workflow.manage', 'org.approvals.action.approve'])
  const canReadAudit = hasPermission(user, 'org.audit.read')

  return [
    {
      label: 'Workspace',
      items: [
        { label: 'Dashboard', href: '/org/dashboard', icon: LayoutDashboard },
        { label: 'Organisation', href: '/org/profile', icon: Building2 },
      ],
    },
    {
      label: 'People',
      items: [
        ...(canReadEmployees ? [{ label: 'Employees', href: '/org/employees', icon: Users }] : []),
        ...(canReadEmployees ? [{ label: 'Org chart', href: '/org/org-chart', icon: GitBranch }] : []),
        ...(canReadEmployees ? [{ label: 'Departments', href: '/org/departments', icon: Building }] : []),
        ...(canReadEmployees ? [{ label: 'Locations', href: '/org/locations', icon: MapPin }] : []),
      ],
    },
    {
      label: 'Time & Leave',
      items: [
        ...(isFeatureEnabled(featureFlags, 'ATTENDANCE') ? [{ label: 'Attendance', href: '/org/attendance', icon: Clock3 }] : []),
        ...(isFeatureEnabled(featureFlags, 'BIOMETRICS') ? [{ label: 'Biometric Devices', href: '/org/biometric-devices', icon: Fingerprint }] : []),
        ...(isFeatureEnabled(featureFlags, 'TIMEOFF')
          ? [
              { label: 'Holidays', href: '/org/holidays', icon: CalendarDays },
              { label: 'Leave cycles', href: '/org/leave-cycles', icon: Repeat },
              { label: 'Leave plans', href: '/org/leave-plans', icon: ClipboardCheck },
              { label: 'OD policies', href: '/org/on-duty-policies', icon: PlaneTakeoff },
            ]
          : []),
      ],
    },
    {
      label: 'Operations',
      items: [
        ...(isFeatureEnabled(featureFlags, 'PAYROLL') && canReadPayroll ? [{ label: 'Payroll Preview', href: '/org/payroll', icon: Landmark }] : []),
        { label: 'Billing', href: '/org/billing', icon: CreditCard },
        { label: 'Expense policies', href: '/org/expenses/policies', icon: ReceiptText },
        { label: 'Expense claims', href: '/org/expenses/claims', icon: ReceiptText },
        { label: 'Assets', href: '/org/assets', icon: BriefcaseBusiness },
        { label: 'Asset assignments', href: '/org/assets/assignments', icon: Wrench },
        ...(isFeatureEnabled(featureFlags, 'RECRUITMENT')
          ? [
              { label: 'Job postings', href: '/org/recruitment/jobs', icon: BriefcaseBusiness },
              { label: 'Applications', href: '/org/recruitment/applications', icon: Users },
            ]
          : []),
        ...(isFeatureEnabled(featureFlags, 'PERFORMANCE')
          ? [
              { label: 'Goal cycles', href: '/org/performance/goals', icon: Target },
              { label: 'Appraisal cycles', href: '/org/performance/appraisals', icon: ClipboardCheck },
            ]
          : []),
        ...(isFeatureEnabled(featureFlags, 'REPORTS') && canReadReports ? [{ label: 'Reports', href: '/org/reports', icon: BarChart3 }] : []),
        ...(isFeatureEnabled(featureFlags, 'APPROVALS') && canAccessApprovals
          ? [{ label: 'Approvals', href: '/org/approval-workflows', icon: ClipboardCheck }]
          : []),
        ...(isFeatureEnabled(featureFlags, 'NOTICES') ? [{ label: 'Notices', href: '/org/notices', icon: Bell }] : []),
        ...(canReadAudit ? [{ label: 'Audit Timeline', href: '/org/audit', icon: ScrollText }] : []),
      ],
    },
  ].filter((group) => group.items.length > 0)
}

export function OrgLayout() {
  const { user, logout, refreshUser } = useAuth()
  const navigate = useNavigate()
  const refreshImpersonationMutation = useRefreshCtImpersonation()
  const stopImpersonationMutation = useStopCtImpersonation()
  const activeImpersonationSessionId = user?.impersonation?.session_id ?? null
  const navGroups = buildNavGroups(user)

  useEffect(() => {
    if (!activeImpersonationSessionId || user?.account_type !== 'CONTROL_TOWER') {
      return
    }
    void refreshImpersonationMutation.mutateAsync().catch(() => undefined)
  }, [activeImpersonationSessionId, user?.account_type])

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  const handleStopImpersonation = async () => {
    try {
      const session = await stopImpersonationMutation.mutateAsync()
      await refreshUser()
      toast.success('Returned to Control Tower.')
      navigate(`/ct/organisations/${session.organisation_id}`, { replace: true })
    } catch {
      toast.error('Unable to stop Control Tower impersonation.')
    }
  }

  return (
    <div className="min-h-screen lg:flex">
      <SidebarNav groups={navGroups} title="Clarisal" subtitle="Organisation Console" />
      <div className="flex min-w-0 flex-1 flex-col px-4 pb-6 lg:pl-0 lg:pr-6">
        <header className="shell-topbar sticky top-4 z-20 mt-0 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Organisation workspace</p>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-base font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">{user?.organisation_name || 'Organisation'}</h1>
              <StatusBadge tone={getAccessStateTone(user?.organisation_access_state)}>
                {user?.organisation_access_state || 'Provisioning'}
              </StatusBadge>
              {isFeatureEnabled(user?.feature_flags, 'ATTENDANCE') ? <StatusBadge tone="success">Attendance live</StatusBadge> : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <NotificationBell />
            <ThemeToggle />
            <WorkspaceSwitcher currentMode="ADMIN" />
            <button onClick={handleLogout} className="btn-secondary px-2.5 py-2" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="page-shell flex-1 py-6">
          {user?.impersonation ? (
            <div className="mb-6 rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-semibold">Control Tower impersonation is active.</p>
                  <p className="mt-1 text-[hsl(var(--muted-foreground))]">
                    Viewing {user.impersonation.organisation_name} in an act-as session. Most writes stay blocked. Started {formatDateTime(user.impersonation.started_at)}.
                  </p>
                  <p className="mt-1 text-[hsl(var(--muted-foreground))]">Reason: {user.impersonation.reason}</p>
                  {user.impersonation.target_org_admin ? (
                    <p className="mt-1 text-[hsl(var(--muted-foreground))]">
                      Target admin: {user.impersonation.target_org_admin.full_name} ({user.impersonation.target_org_admin.email})
                    </p>
                  ) : null}
                  <p className="mt-2 text-[hsl(var(--muted-foreground))]">
                    Allowed CT writes in this session: reactivate inactive admins, reset onboarding steps, and extend paid licence expiry.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link className="btn-secondary" to={`/ct/organisations/${user.impersonation.organisation_id}?tab=admins`}>
                      Reactivate admin
                    </Link>
                    <Link className="btn-secondary" to={`/ct/organisations/${user.impersonation.organisation_id}?tab=onboarding`}>
                      Reset onboarding step
                    </Link>
                    <Link className="btn-secondary" to={`/ct/organisations/${user.impersonation.organisation_id}?tab=licences`}>
                      Extend licence expiry
                    </Link>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void handleStopImpersonation()}
                  disabled={stopImpersonationMutation.isPending}
                  className="btn-secondary"
                >
                  Stop impersonation
                </button>
              </div>
            </div>
          ) : null}
          {user?.org_operations_guard?.admin_mutations_blocked ? (
            <div className="mb-6 rounded-[24px] border border-[hsl(var(--warning)_/_0.32)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
              <p className="font-semibold">Organisation admin actions are currently blocked.</p>
              <p className="mt-1 text-[hsl(var(--muted-foreground))]">{user.org_operations_guard.reason}</p>
            </div>
          ) : null}
          <OrgSetupBanner />
          <Outlet />
        </main>
      </div>
    </div>
  )
}
