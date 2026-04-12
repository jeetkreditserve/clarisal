import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useAuth } from '@/hooks/useAuth'
import {
  assignCtAccessRole,
  createCtAccessRole,
  fetchCtAccessControlOverview,
} from '@/lib/api/access-control'
import { getErrorMessage } from '@/lib/errors'
import { hasAnyPermission, hasPermission } from '@/lib/rbac'

export function CtAccessControlPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canRead = hasAnyPermission(user, ['ct.organisations.read', 'ct.organisations.write'])
  const canWrite = hasPermission(user, 'ct.organisations.write')
  const [roleName, setRoleName] = useState('')
  const [selectedPermissionCodes, setSelectedPermissionCodes] = useState<string[]>([])
  const [assignmentUserId, setAssignmentUserId] = useState('')
  const [assignmentRoleCode, setAssignmentRoleCode] = useState('')

  const overviewQuery = useQuery({ queryKey: ['ct', 'access-control'], queryFn: fetchCtAccessControlOverview, enabled: canRead })
  const createRoleMutation = useMutation({
    mutationFn: createCtAccessRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['ct', 'access-control'] })
    },
  })
  const assignRoleMutation = useMutation({
    mutationFn: assignCtAccessRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['ct', 'access-control'] })
    },
  })

  const overview = overviewQuery.data

  if (!canRead) {
    return <Navigate to="/ct/dashboard" replace />
  }

  const togglePermission = (code: string) => {
    setSelectedPermissionCodes((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]))
  }

  const submitRole = async () => {
    if (!roleName.trim() || selectedPermissionCodes.length === 0) {
      toast.error('Choose a role name and at least one permission.')
      return
    }
    try {
      await createRoleMutation.mutateAsync({
        name: roleName.trim(),
        permission_codes: selectedPermissionCodes,
      })
      toast.success('Control Tower role created.')
      setRoleName('')
      setSelectedPermissionCodes([])
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the Control Tower role.'))
    }
  }

  const submitAssignment = async () => {
    if (!assignmentUserId || !assignmentRoleCode) {
      toast.error('Choose a user and a role.')
      return
    }
    try {
      await assignRoleMutation.mutateAsync({
        user_id: assignmentUserId,
        role_code: assignmentRoleCode,
        is_active: true,
        scopes: [],
      })
      toast.success('Control Tower role assigned.')
      setAssignmentUserId('')
      setAssignmentRoleCode('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to assign the Control Tower role.'))
    }
  }

  if (overviewQuery.isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={8} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Control Tower"
        title="Access control"
        description="Keep tenant support, implementation, billing, and audit access separated across the CT team."
      />

      <SectionCard title="CT roles" description="Seeded roles cover standard support paths; custom roles allow narrower delegation.">
        <div className="grid gap-3">
          {overview?.roles.map((role) => (
            <div key={role.code} className="rounded-[18px] border border-[hsl(var(--border)_/_0.8)] p-4">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">{role.name}</p>
                <StatusBadge tone={role.is_system ? 'info' : 'neutral'}>{role.is_system ? 'System' : 'Custom'}</StatusBadge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {role.permissions.map((permission) => (
                  <StatusBadge key={permission} tone="neutral">
                    {permission}
                  </StatusBadge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <SectionCard title="Create CT role" description="Use only for team-specific access that the seeded roles do not already cover.">
          <div className="grid gap-4">
            <label className="grid gap-2">
              <span className="field-label">Role name</span>
              <input className="field-input" value={roleName} onChange={(event) => setRoleName(event.target.value)} disabled={!canWrite} />
            </label>
            <div className="grid gap-3">
              {overview?.permissions.map((permission) => (
                <label key={permission.code} className="surface-muted flex items-start gap-3 rounded-[18px] p-4">
                  <input
                    type="checkbox"
                    checked={selectedPermissionCodes.includes(permission.code)}
                    onChange={() => togglePermission(permission.code)}
                    disabled={!canWrite}
                  />
                  <span>
                    <span className="block font-medium text-[hsl(var(--foreground-strong))]">{permission.label}</span>
                    <span className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">{permission.code}</span>
                  </span>
                </label>
              ))}
            </div>
            <button type="button" className="btn-primary" onClick={() => void submitRole()} disabled={!canWrite || createRoleMutation.isPending}>
              {createRoleMutation.isPending ? 'Creating...' : 'Create CT role'}
            </button>
          </div>
        </SectionCard>

        <SectionCard title="Assignments" description="Assign seeded or custom CT roles to active Control Tower users.">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="grid gap-2">
              <span className="field-label">User</span>
              <select className="field-input" value={assignmentUserId} onChange={(event) => setAssignmentUserId(event.target.value)} disabled={!canWrite}>
                <option value="">Select a user</option>
                {overview?.users.map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.full_name || candidate.email}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2">
              <span className="field-label">Role</span>
              <select className="field-input" value={assignmentRoleCode} onChange={(event) => setAssignmentRoleCode(event.target.value)} disabled={!canWrite}>
                <option value="">Select a role</option>
                {overview?.roles.map((role) => (
                  <option key={role.code} value={role.code}>
                    {role.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-end">
              <button type="button" className="btn-primary w-full" onClick={() => void submitAssignment()} disabled={!canWrite || assignRoleMutation.isPending}>
                {assignRoleMutation.isPending ? 'Assigning...' : 'Assign CT role'}
              </button>
            </div>
          </div>

          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">
                  <th className="px-3 py-2">User</th>
                  <th className="px-3 py-2">Role</th>
                </tr>
              </thead>
              <tbody>
                {overview?.assignments.map((assignment) => (
                  <tr key={assignment.id} className="border-t border-[hsl(var(--border)_/_0.7)]">
                    <td className="px-3 py-3 font-medium text-[hsl(var(--foreground-strong))]">{assignment.user_email}</td>
                    <td className="px-3 py-3">{assignment.role_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
