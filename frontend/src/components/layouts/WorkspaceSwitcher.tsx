import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BriefcaseBusiness, Building2, UserRound } from 'lucide-react'

import { AppSelect } from '@/components/ui/AppSelect'
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

  const activeAdmin = user.admin_organisations.find((workspace) => workspace.is_active_context) ?? user.admin_organisations[0]
  const activeEmployee = user.employee_workspaces.find((workspace) => workspace.is_active_context) ?? user.employee_workspaces[0]

  const handleSwitch = async (workspace_kind: 'ADMIN' | 'EMPLOYEE', organisation_id: string) => {
    setIsSwitching(true)
    try {
      const nextUser = await switchWorkspace({ workspace_kind, organisation_id })
      if (workspace_kind === 'ADMIN') {
        navigate('/org/dashboard', { replace: true })
      } else if (
        nextUser.active_employee_status === 'INVITED' ||
        (nextUser.active_employee_onboarding_status && nextUser.active_employee_onboarding_status !== 'COMPLETE')
      ) {
        navigate('/me/onboarding', { replace: true })
      } else {
        navigate('/me/dashboard', { replace: true })
      }
      return nextUser
    } finally {
      setIsSwitching(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {user.has_org_admin_access ? (
        <label className="surface-shell flex items-center gap-2 rounded-[20px] px-3 py-2 text-sm text-[hsl(var(--muted-foreground-strong))]">
          <BriefcaseBusiness className="h-4 w-4 text-[hsl(var(--brand))]" />
          <span className="font-medium text-[hsl(var(--muted-foreground))]">Admin</span>
          <AppSelect
            value={activeAdmin?.organisation_id ?? ''}
            onValueChange={(value) => void handleSwitch('ADMIN', value)}
            disabled={isSwitching || user.admin_organisations.length === 0}
            options={user.admin_organisations.map((workspace) => ({
              value: workspace.organisation_id,
              label: workspace.organisation_name,
            }))}
            triggerClassName="min-w-[12rem] border-0 bg-transparent px-0 py-0 shadow-none focus:translate-y-0 focus:bg-transparent focus:shadow-none"
            contentClassName="min-w-[15rem]"
          />
        </label>
      ) : null}

      {user.has_employee_access ? (
        <label className="surface-shell flex items-center gap-2 rounded-[20px] px-3 py-2 text-sm text-[hsl(var(--muted-foreground-strong))]">
          <UserRound className="h-4 w-4 text-[hsl(var(--accent))]" />
          <span className="font-medium text-[hsl(var(--muted-foreground))]">Employee</span>
          <AppSelect
            value={activeEmployee?.organisation_id ?? ''}
            onValueChange={(value) => void handleSwitch('EMPLOYEE', value)}
            disabled={isSwitching || user.employee_workspaces.length === 0}
            options={user.employee_workspaces.map((workspace) => ({
              value: workspace.organisation_id,
              label: workspace.organisation_name,
            }))}
            triggerClassName="min-w-[12rem] border-0 bg-transparent px-0 py-0 shadow-none focus:translate-y-0 focus:bg-transparent focus:shadow-none"
            contentClassName="min-w-[15rem]"
          />
        </label>
      ) : null}

      {currentMode === 'ADMIN' && user.has_employee_access && activeEmployee ? (
        <button
          type="button"
          onClick={() => void handleSwitch('EMPLOYEE', activeEmployee.organisation_id)}
          disabled={isSwitching}
          className="btn-secondary"
        >
          <UserRound className="h-4 w-4" />
          Open employee workspace
        </button>
      ) : null}

      {currentMode === 'EMPLOYEE' && user.has_org_admin_access && activeAdmin ? (
        <button
          type="button"
          onClick={() => void handleSwitch('ADMIN', activeAdmin.organisation_id)}
          disabled={isSwitching}
          className="btn-secondary"
        >
          <Building2 className="h-4 w-4" />
          Open admin workspace
        </button>
      ) : null}
    </div>
  )
}
