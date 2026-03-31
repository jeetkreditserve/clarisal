import { Outlet, useNavigate } from 'react-router-dom'
import { CreditCard, FileText, GraduationCap, IdCard, LayoutDashboard, LogOut, User } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import { useAuth } from '@/hooks/useAuth'
import { StatusBadge } from '@/components/ui/StatusBadge'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/me/dashboard', icon: LayoutDashboard },
  { label: 'Profile', href: '/me/profile', icon: User },
  { label: 'Education', href: '/me/education', icon: GraduationCap },
  { label: 'Identity', href: '/me/profile', icon: IdCard },
  { label: 'Banking', href: '/me/profile', icon: CreditCard },
  { label: 'Documents', href: '/me/documents', icon: FileText },
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
      <SidebarNav items={navItems} title="Calrisal" subtitle="Employee Self-Service" />
      <div className="flex min-w-0 flex-1 flex-col px-4 pb-6 lg:pl-0 lg:pr-6">
        <header className="surface-card sticky top-4 z-20 mt-0 flex flex-col gap-4 rounded-[28px] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Personal workspace</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-semibold tracking-tight text-slate-950">{user?.full_name || 'Employee profile'}</h1>
              <StatusBadge tone="info">{user?.organisation_name || 'Calrisal'}</StatusBadge>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <WorkspaceSwitcher currentMode="EMPLOYEE" />
            <div className="rounded-[20px] bg-slate-950 px-4 py-2 text-right text-sm text-white">
              <p className="font-semibold">{user?.full_name || user?.email}</p>
              <p className="text-xs text-slate-300">{user?.email}</p>
            </div>
            <button onClick={handleLogout} className="btn-secondary">
              <LogOut className="h-4 w-4" />
              Sign out
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
