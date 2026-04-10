import { Outlet, useNavigate } from 'react-router-dom'
import { BriefcaseBusiness, CheckSquare, Clock3, FileText, GraduationCap, LayoutDashboard, LogOut, PlaneTakeoff, Target, User } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { useAuth } from '@/hooks/useAuth'
import { NotificationBell } from '@/components/ui/NotificationBell'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/me/dashboard', icon: LayoutDashboard },
  { label: 'Onboarding', href: '/me/onboarding', icon: CheckSquare },
  { label: 'Profile', href: '/me/profile', icon: User },
  { label: 'Education', href: '/me/education', icon: GraduationCap },
  { label: 'Documents', href: '/me/documents', icon: FileText },
  { label: 'Assets', href: '/me/assets', icon: BriefcaseBusiness },
  { label: 'Tax Declarations', href: '/me/tax-declarations', icon: FileText },
  { label: 'Attendance', href: '/me/attendance', icon: Clock3 },
  { label: 'Performance', href: '/me/performance', icon: Target },
  { label: 'Leave', href: '/me/leave', icon: LayoutDashboard },
  { label: 'On Duty', href: '/me/od', icon: PlaneTakeoff },
  { label: 'Payslips Preview', href: '/me/payslips', icon: FileText },
  { label: 'Approvals', href: '/me/approvals', icon: CheckSquare },
]

export function EmployeeLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="min-h-screen lg:flex">
      <SidebarNav items={navItems} title="Clarisal" subtitle="Employee Self-Service" />
      <div className="flex min-w-0 flex-1 flex-col px-4 pb-6 lg:pl-0 lg:pr-6">
        <header className="shell-topbar sticky top-4 z-20 mt-0 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-base font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">{user?.full_name || 'Employee profile'}</h1>
            <StatusBadge tone="info">{user?.organisation_name || 'Clarisal'}</StatusBadge>
            {user?.active_employee_onboarding_status && user.active_employee_onboarding_status !== 'COMPLETE' ? (
              <StatusBadge tone="warning">{user.active_employee_onboarding_status}</StatusBadge>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <NotificationBell />
            <ThemeToggle />
            <WorkspaceSwitcher currentMode="EMPLOYEE" />
            <button onClick={handleLogout} className="btn-secondary px-2.5 py-2" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="page-shell flex-1 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
