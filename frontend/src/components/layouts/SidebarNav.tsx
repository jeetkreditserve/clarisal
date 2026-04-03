import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronRight, Shield, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

interface SidebarNavProps {
  items?: NavItem[]
  groups?: NavGroup[]
  title: string
  subtitle?: string
}

export function SidebarNav({ items = [], groups = [], title, subtitle }: SidebarNavProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})

  const toggleGroup = (label: string) => {
    setCollapsedGroups((current) => ({ ...current, [label]: !current[label] }))
  }

  return (
    <aside className="sidebar-surface m-4 flex shrink-0 flex-col rounded-[34px] p-4 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] lg:w-[292px]">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24, ease: 'easeOut' }}
        className="rounded-[28px] border border-white/10 bg-white/6 p-5"
      >
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-white/10 p-3 text-[hsl(var(--sidebar-foreground))] ring-1 ring-white/10">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <p className="text-base font-semibold">{title}</p>
            {subtitle ? <p className="text-xs text-[hsl(var(--sidebar-muted))]">{subtitle}</p> : null}
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-[hsl(var(--sidebar-muted))]">
          Govern onboarding, people operations, and document state from a single controlled workspace.
        </p>
      </motion.div>

      <nav className="mt-4 grid gap-3 sm:grid-cols-2 lg:flex lg:flex-1 lg:flex-col">
        {groups.length ? groups.map((group, groupIndex) => {
          const isCollapsed = collapsedGroups[group.label] ?? false
          return (
            <motion.div
              key={group.label}
              initial={{ opacity: 0, x: -14 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.22, delay: 0.05 + groupIndex * 0.03, ease: 'easeOut' }}
              className="rounded-[24px] border border-white/10 bg-white/6 p-2"
            >
              <button
                type="button"
                className="flex w-full items-center justify-between rounded-[18px] px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--sidebar-muted))] transition hover:bg-white/7 hover:text-[hsl(var(--sidebar-foreground))]"
                aria-expanded={!isCollapsed}
                aria-controls={`sidebar-group-${group.label}`}
                onClick={() => toggleGroup(group.label)}
              >
                <span>{group.label}</span>
                <ChevronDown className={cn('h-4 w-4 transition-transform', isCollapsed ? '-rotate-90' : 'rotate-0')} />
              </button>
              <div id={`sidebar-group-${group.label}`} className={cn('mt-2 grid gap-2', isCollapsed && 'hidden')}>
                {group.items.map((item) => (
                  <NavLink
                    key={item.href}
                    to={item.href}
                    className={({ isActive }) =>
                      cn(
                        'group flex items-center justify-between rounded-[22px] px-4 py-3 text-sm transition-all duration-150',
                        isActive
                          ? 'bg-[hsl(var(--sidebar-active-bg))] text-[hsl(var(--sidebar-active-fg))] shadow-[0_18px_34px_rgba(96,165,250,0.22)]'
                          : 'border border-transparent text-[hsl(var(--sidebar-foreground))] hover:border-white/10 hover:bg-white/7'
                      )
                    }
                  >
                    <span className="flex items-center gap-3">
                      <item.icon className="h-4 w-4 shrink-0" />
                      {item.label}
                    </span>
                    <ChevronRight className="h-4 w-4 opacity-40 transition-transform group-hover:translate-x-0.5 group-hover:opacity-80" />
                  </NavLink>
                ))}
              </div>
            </motion.div>
          )
        }) : items.map((item, index) => (
          <motion.div
            key={item.href}
            initial={{ opacity: 0, x: -14 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, delay: 0.05 + index * 0.03, ease: 'easeOut' }}
          >
            <NavLink
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'group flex items-center justify-between rounded-[22px] px-4 py-3 text-sm transition-all duration-150',
                  isActive
                    ? 'bg-[hsl(var(--sidebar-active-bg))] text-[hsl(var(--sidebar-active-fg))] shadow-[0_18px_34px_rgba(96,165,250,0.22)]'
                    : 'border border-transparent text-[hsl(var(--sidebar-foreground))] hover:border-white/10 hover:bg-white/7'
                )
              }
            >
              <span className="flex items-center gap-3">
                <item.icon className="h-4 w-4 shrink-0" />
                {item.label}
              </span>
              <ChevronRight className="h-4 w-4 opacity-40 transition-transform group-hover:translate-x-0.5 group-hover:opacity-80" />
            </NavLink>
          </motion.div>
        ))}
      </nav>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, delay: 0.22, ease: 'easeOut' }}
        className="mt-4 rounded-[28px] border border-white/10 bg-white/6 p-5 text-sm leading-6 text-[hsl(var(--sidebar-muted))]"
      >
        <div className="mb-3 flex items-center gap-2 text-[hsl(var(--sidebar-foreground))]">
          <Sparkles className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-[0.18em]">Guardrails</span>
        </div>
        Organisation access is enforced by session auth, tenant scoping, and backend role checks.
      </motion.div>
    </aside>
  )
}
