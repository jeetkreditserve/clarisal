import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useDepartments, useEmployees, useLocations } from '@/hooks/useOrgAdmin'
import {
  assignOrgAccessRole,
  createOrgAccessRole,
  fetchOrgAccessControlOverview,
} from '@/lib/api/access-control'
import { getErrorMessage } from '@/lib/errors'
import { canManageAccessControl } from '@/lib/rbac'
import type { AccessPermission, AccessRoleAssignmentScopePayload, AccessScopeKind } from '@/types/access-control'
import { useAuth } from '@/hooks/useAuth'

const HIGH_RISK_PERMISSION_CODES = ['org.payroll.process', 'org.employee_sensitive.read', 'org.access_control.manage']
const SCOPE_OPTIONS: Array<{ value: AccessScopeKind; label: string }> = [
  { value: 'ALL_EMPLOYEES', label: 'All employees' },
  { value: 'OWN_RECORD', label: 'Own record' },
  { value: 'REPORTING_TREE', label: 'Reporting tree' },
  { value: 'SELECTED_OFFICE_LOCATIONS', label: 'Selected office location' },
  { value: 'SELECTED_DEPARTMENTS', label: 'Selected department' },
  { value: 'SELECTED_EMPLOYEES', label: 'Selected employee' },
  { value: 'SELECTED_LEGAL_ENTITIES', label: 'Selected legal entity' },
  { value: 'SELECTED_COST_CENTRES', label: 'Selected cost centre' },
  { value: 'SELECTED_EMPLOYMENT_TYPES', label: 'Selected employment type' },
  { value: 'SELECTED_GRADES', label: 'Selected grade' },
  { value: 'SELECTED_BANDS', label: 'Selected band' },
  { value: 'SELECTED_DESIGNATIONS', label: 'Selected designation' },
]

function permissionTone(code: string) {
  return HIGH_RISK_PERMISSION_CODES.includes(code) ? 'warning' : 'neutral'
}

function scopePayload(
  scopeKind: AccessScopeKind,
  scopeValue: string,
): AccessRoleAssignmentScopePayload[] {
  if (!scopeKind || scopeKind === 'ALL_EMPLOYEES') {
    return []
  }
  if (scopeKind === 'SELECTED_OFFICE_LOCATIONS' && scopeValue) {
    return [{ scope_kind: scopeKind, office_location_id: scopeValue }]
  }
  if (scopeKind === 'SELECTED_DEPARTMENTS' && scopeValue) {
    return [{ scope_kind: scopeKind, department_id: scopeValue }]
  }
  if (scopeKind === 'SELECTED_EMPLOYEES' && scopeValue) {
    return [{ scope_kind: scopeKind, employee_id: scopeValue }]
  }
  if (scopeKind === 'OWN_RECORD' || scopeKind === 'REPORTING_TREE') {
    return [{ scope_kind: scopeKind }]
  }
  return scopeValue ? [{ scope_kind: scopeKind, value_text: scopeValue }] : []
}

function PermissionChecklist({
  permissions,
  selected,
  onToggle,
}: {
  permissions: AccessPermission[]
  selected: string[]
  onToggle: (code: string) => void
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {permissions.map((permission) => (
        <label key={permission.code} className="surface-muted flex items-start gap-3 rounded-[18px] p-4">
          <input type="checkbox" checked={selected.includes(permission.code)} onChange={() => onToggle(permission.code)} />
          <span>
            <span className="block font-medium text-[hsl(var(--foreground-strong))]">{permission.label}</span>
            <span className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">{permission.code}</span>
          </span>
        </label>
      ))}
    </div>
  )
}

export function OrgAccessControlPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canManage = canManageAccessControl(user)
  const [roleName, setRoleName] = useState('')
  const [roleDescription, setRoleDescription] = useState('')
  const [selectedPermissionCodes, setSelectedPermissionCodes] = useState<string[]>([])
  const [assignmentUserId, setAssignmentUserId] = useState('')
  const [assignmentRoleCode, setAssignmentRoleCode] = useState('')
  const [scopeKind, setScopeKind] = useState<AccessScopeKind>('ALL_EMPLOYEES')
  const [scopeValue, setScopeValue] = useState('')

  const overviewQuery = useQuery({ queryKey: ['org', 'access-control'], queryFn: fetchOrgAccessControlOverview, enabled: canManage })
  const departmentsQuery = useDepartments(false, canManage)
  const locationsQuery = useLocations(false, canManage)
  const employeesQuery = useEmployees(undefined, canManage)

  const createRoleMutation = useMutation({
    mutationFn: createOrgAccessRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', 'access-control'] })
    },
  })
  const assignRoleMutation = useMutation({
    mutationFn: assignOrgAccessRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['org', 'access-control'] })
    },
  })

  const overview = overviewQuery.data
  const dangerousRoles = useMemo(
    () => overview?.roles.filter((role) => role.permissions.some((permission) => HIGH_RISK_PERMISSION_CODES.includes(permission))) ?? [],
    [overview?.roles],
  )

  if (!canManage) {
    return <Navigate to="/org/dashboard" replace />
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
        description: roleDescription.trim(),
        permission_codes: selectedPermissionCodes,
      })
      toast.success('Access role created.')
      setRoleName('')
      setRoleDescription('')
      setSelectedPermissionCodes([])
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the access role.'))
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
        scopes: scopePayload(scopeKind, scopeValue),
      })
      toast.success('Access role assigned.')
      setAssignmentUserId('')
      setAssignmentRoleCode('')
      setScopeKind('ALL_EMPLOYEES')
      setScopeValue('')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to assign the access role.'))
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
        eyebrow="Access"
        title="Access control"
        description="Create scoped admin roles, review effective assignments, and keep sensitive modules delegated deliberately."
      />

      {dangerousRoles.length > 0 ? (
        <div className="rounded-[22px] border border-[hsl(var(--warning)_/_0.28)] bg-[hsl(var(--warning)_/_0.12)] px-5 py-4 text-sm text-[hsl(var(--foreground-strong))]">
          <p className="font-semibold">High-risk permissions require careful review.</p>
          <p className="mt-1 text-[hsl(var(--muted-foreground))]">
            Payroll processing, sensitive employee fields, and access-control management should only be granted with clear scope limits.
          </p>
        </div>
      ) : null}

      <SectionCard title="Permission matrix" description="Roles are composed from these organisation-scoped permissions.">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">
                <th className="px-3 py-2">Permission</th>
                <th className="px-3 py-2">Resource</th>
                <th className="px-3 py-2">Risk</th>
              </tr>
            </thead>
            <tbody>
              {overview?.permissions.map((permission) => (
                <tr key={permission.code} className="border-t border-[hsl(var(--border)_/_0.7)]">
                  <td className="px-3 py-3 font-medium text-[hsl(var(--foreground-strong))]">{permission.code}</td>
                  <td className="px-3 py-3 text-[hsl(var(--muted-foreground))]">{permission.label}</td>
                  <td className="px-3 py-3">
                    <StatusBadge tone={permissionTone(permission.code)}>
                      {HIGH_RISK_PERMISSION_CODES.includes(permission.code) ? 'High' : 'Standard'}
                    </StatusBadge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionCard title="Roles" description="System roles stay immutable; custom roles can focus on a smaller permission set.">
          <div className="grid gap-3">
            {overview?.roles.map((role) => (
              <div key={role.code} className="rounded-[18px] border border-[hsl(var(--border)_/_0.8)] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{role.name}</p>
                  <StatusBadge tone={role.is_system ? 'info' : 'neutral'}>{role.is_system ? 'System' : 'Custom'}</StatusBadge>
                </div>
                <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{role.description || 'No description'}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {role.permissions.map((permission) => (
                    <StatusBadge key={permission} tone={permissionTone(permission)}>
                      {permission}
                    </StatusBadge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Create role" description="Build a focused custom role from the permission matrix.">
          <div className="grid gap-4">
            <label className="grid gap-2">
              <span className="field-label">Role name</span>
              <input className="field-input" value={roleName} onChange={(event) => setRoleName(event.target.value)} />
            </label>
            <label className="grid gap-2">
              <span className="field-label">Description</span>
              <textarea className="field-input min-h-24" value={roleDescription} onChange={(event) => setRoleDescription(event.target.value)} />
            </label>
            <PermissionChecklist permissions={overview?.permissions ?? []} selected={selectedPermissionCodes} onToggle={togglePermission} />
            <button type="button" className="btn-primary" onClick={() => void submitRole()} disabled={createRoleMutation.isPending}>
              {createRoleMutation.isPending ? 'Creating...' : 'Create role'}
            </button>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Assignments" description="Assign a role and optional scope to a user in the current organisation.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="grid gap-2">
            <span className="field-label">User</span>
            <select className="field-input" value={assignmentUserId} onChange={(event) => setAssignmentUserId(event.target.value)}>
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
            <select className="field-input" value={assignmentRoleCode} onChange={(event) => setAssignmentRoleCode(event.target.value)}>
              <option value="">Select a role</option>
              {overview?.roles.map((role) => (
                <option key={role.code} value={role.code}>
                  {role.name}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2">
            <span className="field-label">Scope kind</span>
            <select
              className="field-input"
              value={scopeKind}
              onChange={(event) => {
                setScopeKind(event.target.value as AccessScopeKind)
                setScopeValue('')
              }}
            >
              {SCOPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2">
            <span className="field-label">Scope value</span>
            {scopeKind === 'SELECTED_OFFICE_LOCATIONS' ? (
              <select className="field-input" value={scopeValue} onChange={(event) => setScopeValue(event.target.value)}>
                <option value="">Select a location</option>
                {(locationsQuery.data ?? []).map((location: { id: string; name: string }) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
            ) : null}
            {scopeKind === 'SELECTED_DEPARTMENTS' ? (
              <select className="field-input" value={scopeValue} onChange={(event) => setScopeValue(event.target.value)}>
                <option value="">Select a department</option>
                {(departmentsQuery.data ?? []).map((department: { id: string; name: string }) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            ) : null}
            {scopeKind === 'SELECTED_EMPLOYEES' ? (
              <select className="field-input" value={scopeValue} onChange={(event) => setScopeValue(event.target.value)}>
                <option value="">Select an employee</option>
                {(employeesQuery.data?.results ?? []).map((employee: { id: string; full_name: string }) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name}
                  </option>
                ))}
              </select>
            ) : null}
            {!['SELECTED_OFFICE_LOCATIONS', 'SELECTED_DEPARTMENTS', 'SELECTED_EMPLOYEES'].includes(scopeKind) ? (
              <input
                className="field-input"
                value={scopeValue}
                onChange={(event) => setScopeValue(event.target.value)}
                placeholder={scopeKind === 'ALL_EMPLOYEES' ? 'No extra value required' : 'Enter scope value'}
                disabled={scopeKind === 'ALL_EMPLOYEES' || scopeKind === 'OWN_RECORD' || scopeKind === 'REPORTING_TREE'}
              />
            ) : null}
          </label>
        </div>
        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="text-sm text-[hsl(var(--muted-foreground))]">
            {overview?.assignments.length ?? 0} active assignment{overview?.assignments.length === 1 ? '' : 's'}
          </div>
          <button type="button" className="btn-primary" onClick={() => void submitAssignment()} disabled={assignRoleMutation.isPending}>
            {assignRoleMutation.isPending ? 'Assigning...' : 'Assign role'}
          </button>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Scopes</th>
              </tr>
            </thead>
            <tbody>
              {overview?.assignments.map((assignment) => (
                <tr key={assignment.id} className="border-t border-[hsl(var(--border)_/_0.7)]">
                  <td className="px-3 py-3 font-medium text-[hsl(var(--foreground-strong))]">{assignment.user_full_name || assignment.user_email}</td>
                  <td className="px-3 py-3">{assignment.role_name}</td>
                  <td className="px-3 py-3 text-[hsl(var(--muted-foreground))]">
                    {assignment.scopes.length > 0 ? assignment.scopes.map((scope) => scope.label).join(', ') : 'All employees'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  )
}
