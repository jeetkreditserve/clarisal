import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { ApprovalDecisionDialog } from '@/components/ui/ApprovalDecisionDialog'
import { AppSelect } from '@/components/ui/AppSelect'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useApprovalInbox,
  useApproveApprovalAction,
  useEmployees,
  useOrgExpenseClaimSummary,
  useOrgExpenseClaims,
  useRejectApprovalAction,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime, formatINR } from '@/lib/format'

function getClaimTone(status: string) {
  switch (status) {
    case 'APPROVED':
      return 'success' as const
    case 'REJECTED':
      return 'danger' as const
    case 'SUBMITTED':
      return 'warning' as const
    case 'CANCELLED':
      return 'neutral' as const
    default:
      return 'info' as const
  }
}

function getReimbursementTone(status: string) {
  switch (status) {
    case 'PAID':
      return 'success' as const
    case 'INCLUDED_IN_PAYROLL':
      return 'info' as const
    case 'PENDING_PAYROLL':
      return 'warning' as const
    default:
      return 'neutral' as const
  }
}

export function ExpenseClaimsPage() {
  const [filters, setFilters] = useState({ status: '', reimbursement_status: '', employee: '' })
  const [selectedClaimIds, setSelectedClaimIds] = useState<string[]>([])
  const { data: claims = [], isLoading: claimsLoading } = useOrgExpenseClaims(
    {
      status: filters.status || undefined,
      reimbursement_status: filters.reimbursement_status || undefined,
      employee: filters.employee || undefined,
    },
  )
  const { data: summary, isLoading: summaryLoading } = useOrgExpenseClaimSummary()
  const { data: inbox = [] } = useApprovalInbox()
  const { data: employees } = useEmployees({ status: 'ACTIVE', page: 1 })
  const approveMutation = useApproveApprovalAction()
  const rejectMutation = useRejectApprovalAction()

  const employeeOptions = useMemo(
    () => [{ value: '', label: 'All employees' }, ...((employees?.results ?? []).map((employee) => ({ value: employee.id, label: employee.full_name, hint: employee.employee_code || employee.designation })) )],
    [employees],
  )
  const approvalActionsByRun = useMemo(
    () =>
      new Map(
        inbox
          .filter((item) => item.request_kind === 'EXPENSE_CLAIM' && item.status === 'PENDING')
          .map((item) => [item.approval_run_id, item]),
      ),
    [inbox],
  )

  const pageLoading = claimsLoading || summaryLoading

  const decideClaim = async (approvalRunId: string | null, decision: 'approve' | 'reject', comment = '') => {
    if (!approvalRunId) {
      throw new Error('No approval action is available for this claim.')
    }
    const action = approvalActionsByRun.get(approvalRunId)
    if (!action) {
      throw new Error('The pending approval action could not be found.')
    }
    if (decision === 'approve') {
      await approveMutation.mutateAsync({ actionId: action.id, comment })
      toast.success('Expense claim approved.')
      return
    }
    await rejectMutation.mutateAsync({ actionId: action.id, comment })
    toast.success('Expense claim rejected.')
  }

  const handleBulkApprove = async () => {
    const selectedClaims = claims.filter((claim) => selectedClaimIds.includes(claim.id))
    try {
      for (const claim of selectedClaims) {
        await decideClaim(claim.approval_run_id, 'approve')
      }
      setSelectedClaimIds([])
      toast.success('Selected expense claims approved.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to approve the selected expense claims.'))
    }
  }

  if (pageLoading) {
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
        eyebrow="Expenses"
        title="Expense claims"
        description="Review submitted claims, route decisions through the approval engine, and track which approved reimbursements have moved into payroll."
        actions={
          selectedClaimIds.length ? (
            <button type="button" className="btn-primary" onClick={() => void handleBulkApprove()}>
              Approve selected
            </button>
          ) : null
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <SectionCard title="Claims" description="All claims in the current organisation.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{summary?.total_claims ?? 0}</p>
        </SectionCard>
        <SectionCard title="Total amount" description="Claimed value across statuses.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{formatINR(summary?.total_amount ?? '0')}</p>
        </SectionCard>
        <SectionCard title="Pending payroll" description="Approved claims not yet paid.">
          <p className="text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
            {summary?.by_reimbursement_status?.PENDING_PAYROLL?.count ?? 0}
          </p>
        </SectionCard>
      </div>

      <SectionCard title="Review queue" description="Claims stay linked to the same approval workflow engine used elsewhere in the platform.">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="field-label" htmlFor="expense-filter-status">Claim status</label>
            <AppSelect
              id="expense-filter-status"
              value={filters.status}
              onValueChange={(value) => setFilters((current) => ({ ...current, status: value }))}
              options={[
                { value: '', label: 'All statuses' },
                { value: 'DRAFT', label: 'Draft' },
                { value: 'SUBMITTED', label: 'Submitted' },
                { value: 'APPROVED', label: 'Approved' },
                { value: 'REJECTED', label: 'Rejected' },
                { value: 'CANCELLED', label: 'Cancelled' },
              ]}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="expense-filter-reimbursement">Reimbursement status</label>
            <AppSelect
              id="expense-filter-reimbursement"
              value={filters.reimbursement_status}
              onValueChange={(value) => setFilters((current) => ({ ...current, reimbursement_status: value }))}
              options={[
                { value: '', label: 'All reimbursement states' },
                { value: 'NOT_READY', label: 'Not ready' },
                { value: 'PENDING_PAYROLL', label: 'Pending payroll' },
                { value: 'INCLUDED_IN_PAYROLL', label: 'Included in payroll' },
                { value: 'PAID', label: 'Paid' },
              ]}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="expense-filter-employee">Employee</label>
            <AppSelect
              id="expense-filter-employee"
              value={filters.employee}
              onValueChange={(value) => setFilters((current) => ({ ...current, employee: value }))}
              options={employeeOptions}
            />
          </div>
        </div>

        {claims.length ? (
          <div className="mt-5 space-y-4">
            {claims.map((claim) => {
              const pendingAction = claim.approval_run_id ? approvalActionsByRun.get(claim.approval_run_id) : undefined
              const isSelectable = Boolean(pendingAction)
              return (
                <div key={claim.id} className="rounded-[24px] border border-[hsl(var(--border))] bg-white/70 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      {isSelectable ? (
                        <input
                          type="checkbox"
                          checked={selectedClaimIds.includes(claim.id)}
                          onChange={(event) =>
                            setSelectedClaimIds((current) =>
                              event.target.checked ? [...current, claim.id] : current.filter((id) => id !== claim.id),
                            )
                          }
                          className="mt-1"
                        />
                      ) : null}
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold text-[hsl(var(--foreground-strong))]">{claim.title}</p>
                          <StatusBadge tone={getClaimTone(claim.status)}>{claim.status}</StatusBadge>
                          <StatusBadge tone={getReimbursementTone(claim.reimbursement_status)}>{claim.reimbursement_status}</StatusBadge>
                        </div>
                        <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                          {claim.employee_name} ({claim.employee_code || 'No code'}) • {claim.claim_date} • {formatINR(claim.total_amount)}
                        </p>
                        <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                          {claim.lines.length} line{claim.lines.length !== 1 ? 's' : ''}{claim.reimbursement_pay_run_id ? ` • Payroll run ${claim.reimbursement_pay_run_id}` : ''}
                        </p>
                        {claim.rejection_reason ? (
                          <p className="mt-2 text-sm text-[hsl(var(--danger))]">Decision note: {claim.rejection_reason}</p>
                        ) : null}
                      </div>
                    </div>
                    {pendingAction ? (
                      <div className="flex flex-wrap gap-2">
                        <ApprovalDecisionDialog
                          actionLabel="Approve expense claim"
                          triggerClassName="btn-secondary"
                          triggerLabel="Approve"
                          title="Approve expense claim?"
                          description="Approval moves this claim into the payroll reimbursement queue."
                          confirmLabel="Approve claim"
                          onSubmit={(comment) => decideClaim(claim.approval_run_id, 'approve', comment)}
                        />
                        <ApprovalDecisionDialog
                          actionLabel="Reject expense claim"
                          triggerClassName="btn-secondary"
                          triggerLabel="Reject"
                          title="Reject expense claim?"
                          description="Rejected claims return to the employee for edits and re-submission."
                          confirmLabel="Reject claim"
                          confirmTone="danger"
                          isCommentRequired={true}
                          onSubmit={(comment) => decideClaim(claim.approval_run_id, 'reject', comment)}
                        />
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-4 grid gap-3">
                    {claim.lines.map((line) => (
                      <div key={line.id} className="rounded-[18px] border border-[hsl(var(--border)_/_0.72)] px-4 py-3">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-[hsl(var(--foreground-strong))]">{line.category_name}</p>
                            <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                              {line.expense_date} • {line.merchant || 'Merchant not captured'} • {formatINR(line.amount)}
                            </p>
                            {line.description ? <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">{line.description}</p> : null}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {line.receipts.map((receipt) => (
                              <a key={receipt.id} className="btn-secondary" href={receipt.download_url} target="_blank" rel="noreferrer">
                                {receipt.file_name}
                              </a>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="mt-5">
            <EmptyState title="No expense claims match the filters" description="Submitted, approved, and payroll-linked claims will appear here once employees start using the expense workflow." />
          </div>
        )}
      </SectionCard>
    </div>
  )
}
