import { Outlet, useNavigate } from 'react-router-dom'
import { Bell, Building, Building2, CalendarDays, ClipboardCheck, Clock3, Landmark, LayoutDashboard, LogOut, MapPin, PlaneTakeoff, Repeat, ScrollText, Users } from 'lucide-react'
import { SidebarNav, type NavGroup } from './SidebarNav'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { useAuth } from '@/hooks/useAuth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { NotificationBell } from '@/components/ui/NotificationBell'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { getAccessStateTone } from '@/lib/status'
import { OrgSetupBanner } from '@/components/org/OrgSetupBanner'

const navGroups: NavGroup[] = [
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
      { label: 'Employees', href: '/org/employees', icon: Users },
      { label: 'Departments', href: '/org/departments', icon: Building },
      { label: 'Locations', href: '/org/locations', icon: MapPin },
    ],
  },
  {
    label: 'Time & Leave',
    items: [
      { label: 'Attendance', href: '/org/attendance', icon: Clock3 },
      { label: 'Holidays', href: '/org/holidays', icon: CalendarDays },
      { label: 'Leave cycles', href: '/org/leave-cycles', icon: Repeat },
      { label: 'Leave plans', href: '/org/leave-plans', icon: ClipboardCheck },
      { label: 'OD policies', href: '/org/on-duty-policies', icon: PlaneTakeoff },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Payroll Preview', href: '/org/payroll', icon: Landmark },
      { label: 'Approvals', href: '/org/approval-workflows', icon: ClipboardCheck },
      { label: 'Notices', href: '/org/notices', icon: Bell },
      { label: 'Audit Timeline', href: '/org/audit', icon: ScrollText },
    ],
  },
]

export function OrgLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="min-h-screen lg:flex">
      <SidebarNav groups={navGroups} title="Clarisal" subtitle="Organisation Console" />
      <div className="flex min-w-0 flex-1 flex-col px-4 pb-6 lg:pl-0 lg:pr-6">
        <header className="shell-topbar sticky top-4 z-20 mt-0 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Organisation workspace</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">{user?.organisation_name || 'Organisation'}</h1>
              <StatusBadge tone={getAccessStateTone(user?.organisation_access_state)}>
                {user?.organisation_access_state || 'Provisioning'}
              </StatusBadge>
              <StatusBadge tone="info">Attendance live</StatusBadge>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <NotificationBell />
            <ThemeToggle />
            <WorkspaceSwitcher currentMode="ADMIN" />
            <div className="shell-user-card rounded-[22px] px-4 py-2 text-right text-sm">
              <p className="font-semibold">{user?.full_name || 'Organisation Admin'}</p>
              <p className="text-xs opacity-80">{user?.email}</p>
            </div>
            <button onClick={handleLogout} className="btn-secondary">
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </header>
        <main className="page-shell flex-1 py-6">
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
