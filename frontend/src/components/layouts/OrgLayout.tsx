import { Outlet } from 'react-router-dom'
import { LayoutDashboard, MapPin, Building, Users, LogOut } from 'lucide-react'
import { SidebarNav, type NavItem } from './SidebarNav'
import { useAuth } from '@/hooks/useAuth'
import { useNavigate } from 'react-router-dom'

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/org/dashboard', icon: LayoutDashboard },
  { label: 'Locations', href: '/org/locations', icon: MapPin },
  { label: 'Departments', href: '/org/departments', icon: Building },
  { label: 'Employees', href: '/org/employees', icon: Users },
]

export function OrgLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))]">
      <SidebarNav items={navItems} title="Calrisal" subtitle="HR Portal" />
      <div className="flex flex-1 flex-col overflow-hidden pl-64">
        <header className="flex h-16 items-center justify-between border-b bg-background px-6">
          <div />
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
