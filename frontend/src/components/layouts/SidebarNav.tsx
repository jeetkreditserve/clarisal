import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { ChevronRight, Shield } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
}

interface SidebarNavProps {
  items: NavItem[]
  title: string
  subtitle?: string
}

export function SidebarNav({ items, title, subtitle }: SidebarNavProps) {
  return (
    <aside className="surface-card m-4 flex shrink-0 flex-col rounded-[32px] bg-[linear-gradient(180deg,#0a1422_0%,#0d2133_50%,#15334c_100%)] p-4 text-[hsl(var(--sidebar-foreground))] lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] lg:w-[280px]">
      <div className="rounded-[24px] border border-white/10 bg-white/7 p-5">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-cyan-300/14 p-3 text-cyan-200 ring-1 ring-cyan-200/12">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <p className="text-base font-semibold">{title}</p>
            {subtitle ? <p className="text-xs text-slate-300">{subtitle}</p> : null}
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-slate-300">
          Govern onboarding, people operations, and document state from a single controlled workspace.
        </p>
      </div>

      <nav className="mt-4 grid gap-2 sm:grid-cols-2 lg:flex lg:flex-1 lg:flex-col">
        {items.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'group flex items-center justify-between rounded-[20px] px-4 py-3 text-sm transition-all duration-150',
                isActive
                  ? 'bg-cyan-300/90 text-slate-950 shadow-[0_10px_22px_rgba(103,232,249,0.22)]'
                  : 'border border-transparent text-slate-200 hover:border-white/8 hover:bg-white/7 hover:text-white'
              )
            }
          >
            <span className="flex items-center gap-3">
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </span>
            <ChevronRight className="h-4 w-4 opacity-40 transition-transform group-hover:translate-x-0.5 group-hover:opacity-70" />
          </NavLink>
        ))}
      </nav>

      <div className="mt-4 rounded-[24px] border border-white/10 bg-white/7 p-5 text-sm leading-6 text-slate-300">
        Organisation access is enforced by session auth, tenant scoping, and backend role checks.
      </div>
    </aside>
  )
}
