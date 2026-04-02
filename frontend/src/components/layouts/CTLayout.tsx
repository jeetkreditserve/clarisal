import { Outlet, useNavigate } from 'react-router-dom'
import { Building2, Landmark, LayoutDashboard, LogOut } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { useAuth } from '@/hooks/useAuth'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/ct/dashboard', icon: LayoutDashboard },
  { label: 'Payroll', href: '/ct/payroll', icon: Landmark },
  { label: 'Organisations', href: '/ct/organisations', icon: Building2 },
]

export function CTLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/ct/login')
  }

  return (
    <div className="min-h-screen lg:flex">
      <SidebarNav items={navItems} title="Clarisal" subtitle="Control Tower" />
      <div className="flex min-w-0 flex-1 flex-col px-4 pb-6 lg:pl-0 lg:pr-6">
        <header className="shell-topbar sticky top-4 z-20 mt-0 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Platform operations</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-semibold tracking-tight text-[hsl(var(--foreground-strong))]">Control Tower</h1>
              <StatusBadge tone="info">Global access</StatusBadge>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ThemeToggle />
            <a href="/admin/" className="btn-secondary">
              Django admin
            </a>
            <div className="shell-user-card rounded-[22px] px-4 py-2 text-right text-sm">
              <p className="font-semibold">{user?.full_name || 'Control Tower'}</p>
              <p className="text-xs opacity-80">{user?.email}</p>
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
