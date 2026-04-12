import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PackageCheck } from 'lucide-react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useAssetAssignments,
  useAssetItems,
  useCreateAssetAssignment,
  useEmployees,
  useMarkAssetAssignmentLost,
  useReturnAssetAssignment,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, formatDateTime } from '@/lib/format'
import { getAssetAssignmentTone, getAssetLifecycleTone } from '@/lib/status'

export function AssetAssignmentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedEmployee, setSelectedEmployee] = useState(searchParams.get('employee') ?? '')
  const [selectedStatus, setSelectedStatus] = useState(searchParams.get('status') ?? 'ACTIVE')
  const [assignmentForm, setAssignmentForm] = useState({
    asset_id: '',
    employee_id: searchParams.get('employee') ?? '',
    expected_return_date: '',
    condition_on_issue: 'GOOD',
    notes: '',
  })

  useEffect(() => {
    const nextParams = new URLSearchParams()
    if (selectedEmployee) {
      nextParams.set('employee', selectedEmployee)
    }
    if (selectedStatus) {
      nextParams.set('status', selectedStatus)
    }
    setSearchParams(nextParams, { replace: true })
  }, [selectedEmployee, selectedStatus, setSearchParams])

  const { data: assignments = [], isLoading } = useAssetAssignments({
    employee: selectedEmployee || undefined,
    status: selectedStatus || undefined,
  })
  const { data: items = [] } = useAssetItems({ status: 'AVAILABLE' })
  const { data: employeesResponse } = useEmployees({ status: 'ACTIVE', page: 1 })
  const createAssignmentMutation = useCreateAssetAssignment()
  const returnAssetMutation = useReturnAssetAssignment()
  const markLostMutation = useMarkAssetAssignmentLost()

  const employeeOptions = useMemo(
    () =>
      (employeesResponse?.results ?? []).map((employee) => ({
        id: employee.id,
        label: employee.employee_code ? `${employee.full_name} (${employee.employee_code})` : employee.full_name,
      })),
    [employeesResponse],
  )

  const handleAssignAsset = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createAssignmentMutation.mutateAsync({
        asset_id: assignmentForm.asset_id,
        employee_id: assignmentForm.employee_id,
        expected_return_date: assignmentForm.expected_return_date || null,
        condition_on_issue: assignmentForm.condition_on_issue,
        notes: assignmentForm.notes,
      })
      toast.success('Asset assigned to employee.')
      setAssignmentForm({
        asset_id: '',
        employee_id: selectedEmployee,
        expected_return_date: '',
        condition_on_issue: 'GOOD',
        notes: '',
      })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to assign this asset right now.'))
    }
  }

  const handleReturn = async (assignmentId: string) => {
    try {
      await returnAssetMutation.mutateAsync({
        id: assignmentId,
        payload: {
          condition_on_return: 'GOOD',
          notes: '',
        },
      })
      toast.success('Asset return recorded.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to record the asset return.'))
    }
  }

  const handleMarkLost = async (assignmentId: string) => {
    try {
      await markLostMutation.mutateAsync({
        id: assignmentId,
        payload: {
          notes: 'Marked lost from assignment workspace.',
        },
      })
      toast.success('Asset marked as lost.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to mark this asset as lost.'))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Asset assignments"
        description="Issue inventory to employees, filter custody records by assignee, and record returns or losses when devices change hands."
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Issue asset" description="Assign only available stock and capture the expected recovery date up front.">
          <form className="grid gap-4" onSubmit={handleAssignAsset}>
            <div>
              <label className="field-label" htmlFor="assignment-asset">
                Asset
              </label>
              <select
                id="assignment-asset"
                className="field-input"
                value={assignmentForm.asset_id}
                onChange={(event) => setAssignmentForm((current) => ({ ...current, asset_id: event.target.value }))}
              >
                <option value="">Select asset</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.asset_tag || 'no tag'})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="assignment-employee">
                Employee
              </label>
              <select
                id="assignment-employee"
                className="field-input"
                value={assignmentForm.employee_id}
                onChange={(event) => setAssignmentForm((current) => ({ ...current, employee_id: event.target.value }))}
              >
                <option value="">Select employee</option>
                {employeeOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="assignment-expected-return">
                Expected return date
              </label>
              <input
                id="assignment-expected-return"
                type="date"
                className="field-input"
                value={assignmentForm.expected_return_date}
                onChange={(event) => setAssignmentForm((current) => ({ ...current, expected_return_date: event.target.value }))}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="assignment-notes">
                Notes
              </label>
              <textarea
                id="assignment-notes"
                className="field-input min-h-[104px]"
                value={assignmentForm.notes}
                onChange={(event) => setAssignmentForm((current) => ({ ...current, notes: event.target.value }))}
                placeholder="Return to IT on exit or role change."
              />
            </div>
            <button type="submit" className="btn-primary" disabled={createAssignmentMutation.isPending}>
              Assign asset
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Assignment ledger" description="Filter by employee or status to focus on unresolved custody and offboarding recovery.">
          <div className="mb-5 grid gap-4 md:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="assignment-employee-filter">
                Employee filter
              </label>
              <select
                id="assignment-employee-filter"
                className="field-input"
                value={selectedEmployee}
                onChange={(event) => {
                  const value = event.target.value
                  setSelectedEmployee(value)
                  setAssignmentForm((current) => ({ ...current, employee_id: value }))
                }}
              >
                <option value="">All employees</option>
                {employeeOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="assignment-status-filter">
                Status filter
              </label>
              <select id="assignment-status-filter" className="field-input" value={selectedStatus} onChange={(event) => setSelectedStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="RETURNED">Returned</option>
                <option value="LOST">Lost</option>
              </select>
            </div>
          </div>

          {assignments.length ? (
            <div className="space-y-4">
              {assignments.map((assignment) => (
                <div key={assignment.id} className="rounded-[24px] border border-[hsl(var(--border))] bg-white/70 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{assignment.asset_name}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                        {assignment.asset_tag || 'No asset tag'} • {assignment.employee_name}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge tone={getAssetAssignmentTone(assignment.status)}>{assignment.status}</StatusBadge>
                      <StatusBadge tone={assignment.acknowledged_at ? 'success' : 'warning'}>
                        {assignment.acknowledged_at ? 'Acknowledged' : 'Pending acknowledgement'}
                      </StatusBadge>
                    </div>
                  </div>

                  <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div>
                      <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Issued at</dt>
                      <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDateTime(assignment.assigned_at)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Expected return</dt>
                      <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDate(assignment.expected_return_date)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Condition on issue</dt>
                      <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{assignment.condition_on_issue}</dd>
                    </div>
                  </dl>

                  {assignment.notes ? <p className="mt-4 text-sm text-[hsl(var(--muted-foreground))]">{assignment.notes}</p> : null}

                  {assignment.status === 'ACTIVE' ? (
                    <div className="mt-4 flex flex-wrap gap-3">
                      <ConfirmDialog
                        title="Record asset return?"
                        description="Use this after the item is physically recovered so offboarding and audit traces can move forward."
                        confirmLabel="Confirm return"
                        variant="primary"
                        onConfirm={() => handleReturn(assignment.id)}
                        trigger={<button type="button" className="btn-primary">Return asset</button>}
                      />
                      <ConfirmDialog
                        title="Mark this assignment as lost?"
                        description="This keeps the custody trail intact while flagging the asset for investigation or recovery."
                        confirmLabel="Confirm loss"
                        onConfirm={() => handleMarkLost(assignment.id)}
                        trigger={<button type="button" className="btn-secondary">Mark lost</button>}
                      />
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={PackageCheck}
              title="No assignments match these filters"
              description="Issue an asset to start a new custody record or relax the current employee and status filters."
            />
          )}
        </SectionCard>
      </div>

      <SectionCard title="Available stock snapshot" description="Quickly inspect what is ready to issue from inventory without navigating away.">
        {items.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {items.map((item) => (
              <div key={item.id} className="rounded-[20px] border border-[hsl(var(--border))] bg-white/70 px-4 py-4">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">{item.name}</p>
                <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{item.asset_tag || 'No asset tag'}</p>
                <div className="mt-3">
                  <StatusBadge tone={getAssetLifecycleTone(item.lifecycle_status)}>{item.lifecycle_status}</StatusBadge>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={PackageCheck}
            title="No available stock"
            description="Add inventory or close outstanding assignments to make more assets available for issue."
          />
        )}
      </SectionCard>
    </div>
  )
}
