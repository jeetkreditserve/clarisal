import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { BriefcaseBusiness, Check, ChevronsUpDown, UserRound } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

interface WorkspaceSwitcherProps {
  currentMode: 'ADMIN' | 'EMPLOYEE'
}

export function WorkspaceSwitcher({ currentMode }: WorkspaceSwitcherProps) {
  const navigate = useNavigate()
  const { user, switchWorkspace } = useAuth()
  const [isSwitching, setIsSwitching] = useState(false)

  if (!user || user.account_type !== 'WORKFORCE') {
    return null
  }

  const activeAdmin = user.admin_organisations.find((ws) => ws.is_active_context) ?? user.admin_organisations[0]
  const activeEmployee = user.employee_workspaces.find((ws) => ws.is_active_context) ?? user.employee_workspaces[0]

  const currentLabel =
    currentMode === 'ADMIN'
      ? (activeAdmin?.organisation_name ?? 'Admin workspace')
      : (activeEmployee?.organisation_name ?? 'My workspace')

  const CurrentIcon = currentMode === 'ADMIN' ? BriefcaseBusiness : UserRound

  const handleSwitch = async (workspace_kind: 'ADMIN' | 'EMPLOYEE', organisation_id: string) => {
    setIsSwitching(true)
    try {
      const nextUser = await switchWorkspace({ workspace_kind, organisation_id })
      if (workspace_kind === 'ADMIN') {
        navigate(nextUser.default_route || '/org/dashboard', { replace: true })
      } else if (
        nextUser.active_employee_status === 'INVITED' ||
        (nextUser.active_employee_onboarding_status && nextUser.active_employee_onboarding_status !== 'COMPLETE')
      ) {
        navigate('/me/onboarding', { replace: true })
      } else {
        navigate('/me/dashboard', { replace: true })
      }
    } finally {
      setIsSwitching(false)
    }
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          disabled={isSwitching}
          className="surface-shell flex items-center gap-2 rounded-[20px] px-3 py-2 text-sm disabled:opacity-60"
        >
          <CurrentIcon className="h-4 w-4 flex-shrink-0 text-[hsl(var(--brand))]" />
          <span className="max-w-[9rem] truncate font-medium text-[hsl(var(--foreground-strong))]">{currentLabel}</span>
          <ChevronsUpDown className="h-3.5 w-3.5 flex-shrink-0 text-[hsl(var(--muted-foreground))]" />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          sideOffset={8}
          align="end"
          className="z-50 min-w-[14rem] rounded-[18px] border border-[hsl(var(--border))] bg-[hsl(var(--surface))] p-1.5 shadow-[var(--shadow-card)]"
        >
          {user.admin_organisations.length > 0 && (
            <>
              <DropdownMenu.Label className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[hsl(var(--muted-foreground))]">
                Admin workspaces
              </DropdownMenu.Label>
              {user.admin_organisations.map((ws) => {
                const isActive = currentMode === 'ADMIN' && ws.organisation_id === activeAdmin?.organisation_id
                return (
                  <DropdownMenu.Item
                    key={ws.organisation_id}
                    onSelect={() => void handleSwitch('ADMIN', ws.organisation_id)}
                    className="flex cursor-pointer items-center gap-2 rounded-[12px] px-2 py-2 text-sm outline-none hover:bg-[hsl(var(--surface-subtle))] focus:bg-[hsl(var(--surface-subtle))]"
                  >
                    <BriefcaseBusiness className="h-4 w-4 flex-shrink-0 text-[hsl(var(--brand))]" />
                    <span className="flex-1 truncate font-medium">{ws.organisation_name}</span>
                    {isActive && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[hsl(var(--brand))]" />}
                  </DropdownMenu.Item>
                )
              })}
            </>
          )}

          {user.admin_organisations.length > 0 && user.employee_workspaces.length > 0 && (
            <div className="my-1.5 border-t border-[hsl(var(--border))]" />
          )}

          {user.employee_workspaces.length > 0 && (
            <>
              <DropdownMenu.Label className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[hsl(var(--muted-foreground))]">
                Employee workspaces
              </DropdownMenu.Label>
              {user.employee_workspaces.map((ws) => {
                const isActive = currentMode === 'EMPLOYEE' && ws.organisation_id === activeEmployee?.organisation_id
                return (
                  <DropdownMenu.Item
                    key={ws.organisation_id}
                    onSelect={() => void handleSwitch('EMPLOYEE', ws.organisation_id)}
                    className="flex cursor-pointer items-center gap-2 rounded-[12px] px-2 py-2 text-sm outline-none hover:bg-[hsl(var(--surface-subtle))] focus:bg-[hsl(var(--surface-subtle))]"
                  >
                    <UserRound className="h-4 w-4 flex-shrink-0 text-[hsl(var(--accent))]" />
                    <span className="flex-1 truncate font-medium">{ws.organisation_name}</span>
                    {isActive && <Check className="h-3.5 w-3.5 flex-shrink-0 text-[hsl(var(--accent))]" />}
                  </DropdownMenu.Item>
                )
              })}
            </>
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
