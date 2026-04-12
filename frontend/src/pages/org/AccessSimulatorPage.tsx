import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useAuth } from '@/hooks/useAuth'
import { useEmployees } from '@/hooks/useOrgAdmin'
import { fetchOrgAccessControlOverview, simulateOrgAccess } from '@/lib/api/access-control'
import { getErrorMessage } from '@/lib/errors'
import { canManageAccessControl } from '@/lib/rbac'

export function AccessSimulatorPage() {
  const { user } = useAuth()
  const canManage = canManageAccessControl(user)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')
  const overviewQuery = useQuery({ queryKey: ['org', 'access-control'], queryFn: fetchOrgAccessControlOverview, enabled: canManage })
  const employeesQuery = useEmployees(undefined, canManage)
  const simulateMutation = useMutation({ mutationFn: simulateOrgAccess })

  if (!canManage) {
    return <Navigate to="/org/dashboard" replace />
  }

  const runSimulation = async () => {
    if (!selectedUserId) {
      toast.error('Choose a user to simulate.')
      return
    }
    try {
      await simulateMutation.mutateAsync({
        user_id: selectedUserId,
        employee_id: selectedEmployeeId || undefined,
      })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to simulate access.'))
    }
  }

  if (overviewQuery.isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const simulation = simulateMutation.data

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Access"
        title="Access simulator"
        description="Check the effective permissions and row scope for a specific user before or after assigning a role."
      />

      <SectionCard title="Run simulation" description="Simulate the current organisation workspace for a selected user.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="grid gap-2">
            <span className="field-label">User</span>
            <select className="field-input" value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
              <option value="">Select a user</option>
              {overviewQuery.data?.users.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name || candidate.email}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2">
            <span className="field-label">Employee check</span>
            <select className="field-input" value={selectedEmployeeId} onChange={(event) => setSelectedEmployeeId(event.target.value)}>
              <option value="">Optional employee check</option>
              {(employeesQuery.data?.results ?? []).map((employee: { id: string; full_name: string }) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end">
            <button type="button" className="btn-primary w-full" onClick={() => void runSimulation()} disabled={simulateMutation.isPending}>
              {simulateMutation.isPending ? 'Running...' : 'Run simulation'}
            </button>
          </div>
        </div>
      </SectionCard>

      {simulation ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title="Effective permissions" description="These are the permission codes available in the current org context.">
            <div className="flex flex-wrap gap-2">
              {simulation.effective_permissions.map((permission) => (
                <StatusBadge key={permission} tone="neutral">
                  {permission}
                </StatusBadge>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Effective scopes" description="Scope summaries reflect the human-readable row limits.">
            <div className="flex flex-wrap gap-2">
              {simulation.effective_scopes.map((scope) => (
                <StatusBadge key={`${scope.kind}-${scope.label}`} tone="info">
                  {scope.label}
                </StatusBadge>
              ))}
            </div>
            {simulation.employee_access ? (
              <div className="mt-4 rounded-[18px] border border-[hsl(var(--border)_/_0.8)] p-4">
                <p className="font-medium text-[hsl(var(--foreground-strong))]">Employee access check</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                  {simulation.employee_access.allowed ? 'In scope' : 'Out of scope'}
                </p>
              </div>
            ) : null}
          </SectionCard>
        </div>
      ) : null}
    </div>
  )
}
