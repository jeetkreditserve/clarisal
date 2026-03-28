import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
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
    <aside className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[hsl(var(--sidebar-background))] border-r border-[hsl(var(--sidebar-border))]">
      <div className="flex h-16 items-center px-6 border-b border-[hsl(var(--sidebar-border))]">
        <div>
          <p className="text-sm font-semibold text-[hsl(var(--sidebar-foreground))]">{title}</p>
          {subtitle && (
            <p className="text-xs text-[hsl(var(--sidebar-foreground))] opacity-60">{subtitle}</p>
          )}
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {items.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-[hsl(var(--sidebar-primary))] text-[hsl(var(--sidebar-primary-foreground))]'
                  : 'text-[hsl(var(--sidebar-foreground))] opacity-70 hover:opacity-100 hover:bg-[hsl(var(--sidebar-accent))]'
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
