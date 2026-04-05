import { useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { ApprovalDecisionDialog } from '@/components/ui/ApprovalDecisionDialog'
import { AppCheckbox } from '@/components/ui/AppCheckbox'
import { AppSelect } from '@/components/ui/AppSelect'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useApprovalInbox,
  useApprovalDelegations,
  useApprovalWorkflows,
  useApproveApprovalAction,
  useCreateApprovalDelegation,
  useEmployees,
  useRejectApprovalAction,
  useUpdateApprovalDelegation,
} from '@/hooks/useOrgAdmin'
import { useCtOrgConfiguration } from '@/hooks/useCtOrganisations'
import { APPROVAL_REQUEST_KIND_OPTIONS } from '@/lib/constants'
import { getErrorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'
import { getApprovalActionTone } from '@/lib/status'

const ORG_TABS = [
  { id: 'workflows', label: 'Workflows' },
  { id: 'inbox', label: 'Inbox' },
  { id: 'settings', label: 'Settings' },
] as const

const CT_TABS = [
  { id: 'workflows', label: 'Workflows' },
  { id: 'settings', label: 'Settings' },
] as const

export function ApprovalWorkflowsPage() {
  const navigate = useNavigate()
  const { organisationId } = useParams()
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const tabs = isCtMode ? CT_TABS : ORG_TABS
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = tabs.some((tab) => tab.id === searchParams.get('tab')) ? searchParams.get('tab') : 'workflows'
  const { data: workflows, isLoading } = useApprovalWorkflows(!isCtMode)
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const { data: inbox } = useApprovalInbox(!isCtMode)
  const { data: approvalDelegations = [] } = useApprovalDelegations(!isCtMode)
  const { data: employees } = useEmployees({ status: 'ACTIVE', page: 1 }, !isCtMode)
  const approveMutation = useApproveApprovalAction()
  const rejectMutation = useRejectApprovalAction()
  const createDelegationMutation = useCreateApprovalDelegation()
  const updateDelegationMutation = useUpdateApprovalDelegation()
  const resolvedWorkflows = isCtMode ? configuration?.approval_workflows : workflows
  const pageLoading = isCtMode ? isCtLoading : isLoading
  const [delegationForm, setDelegationForm] = useState({
    delegator_employee_id: '',
    delegate_employee_id: '',
    request_kinds: ['LEAVE'],
    start_date: '',
    end_date: '',
    is_active: true,
  })

  const health = useMemo(() => {
    const workflowList = resolvedWorkflows ?? []
    return {
      active: workflowList.filter((workflow) => workflow.is_active).length,
      defaults: workflowList.filter((workflow) => workflow.is_default).length,
      rules: workflowList.reduce((sum, workflow) => sum + workflow.rules.length, 0),
      stages: workflowList.reduce((sum, workflow) => sum + workflow.stages.length, 0),
    }
  }, [resolvedWorkflows])
  const employeeOptions = useMemo(
    () => [{ value: '', label: 'Select employee' }, ...((employees?.results ?? []).map((employee) => ({ value: employee.id, label: employee.full_name, hint: employee.designation })))],
    [employees],
  )

  const saveDelegation = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createDelegationMutation.mutateAsync({
        delegator_employee_id: delegationForm.delegator_employee_id,
        delegate_employee_id: delegationForm.delegate_employee_id,
        request_kinds: delegationForm.request_kinds,
        start_date: delegationForm.start_date,
        end_date: delegationForm.end_date || null,
        is_active: delegationForm.is_active,
      })
      toast.success('Approval delegation saved.')
      setDelegationForm({
        delegator_employee_id: '',
        delegate_employee_id: '',
        request_kinds: ['LEAVE'],
        start_date: '',
        end_date: '',
        is_active: true,
      })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to save the approval delegation.'))
    }
  }

  const toggleDelegation = async (delegationId: string, nextActive: boolean, currentValues: {
    delegator_employee: string
    delegate_employee: string
    request_kinds: string[]
    start_date: string
    end_date: string | null
  }) => {
    try {
      await updateDelegationMutation.mutateAsync({
        id: delegationId,
        payload: {
          delegator_employee_id: currentValues.delegator_employee,
          delegate_employee_id: currentValues.delegate_employee,
          request_kinds: currentValues.request_kinds,
          start_date: currentValues.start_date,
          end_date: currentValues.end_date,
          is_active: nextActive,
        },
      })
      toast.success('Delegation updated.')
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to update the delegation.'))
    }
  }

  if (pageLoading) {
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
        eyebrow={isCtMode ? 'Control Tower • Approvals' : 'Approvals'}
        title="Approvals"
        description="Separate workflow design from day-to-day approval work so admins can maintain routing without losing operational visibility."
        actions={
          <>
            {isCtMode ? (
              <button type="button" className="btn-secondary" onClick={() => navigate(basePath)}>
                Back to organisation
              </button>
            ) : null}
            {activeTab === 'workflows' ? (
              <button type="button" className="btn-primary" onClick={() => navigate(`${basePath}/approval-workflows/new`)}>
                Build workflow
              </button>
            ) : null}
          </>
        }
      />

      <div className="flex flex-wrap gap-2 rounded-[24px] border border-[hsl(var(--border)_/_0.72)] bg-[hsl(var(--surface))] p-2">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSearchParams({ tab: tab.id })}
              className={
                isActive
                  ? 'rounded-[18px] bg-[hsl(var(--brand))] px-4 py-2 text-sm font-medium text-[hsl(var(--brand-foreground))]'
                  : 'rounded-[18px] px-4 py-2 text-sm font-medium text-[hsl(var(--muted-foreground))] transition hover:bg-[hsl(var(--surface-subtle))]'
              }
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {activeTab === 'workflows' ? (
        <SectionCard title="Workflow catalogue" description="Open dedicated builders to manage rules, stages, fallback behavior, and approver structure.">
          <div className="space-y-4">
            {(resolvedWorkflows ?? []).map((workflow) => (
              <div key={workflow.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                      <p className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{workflow.name}</p>
                      {workflow.is_default ? <StatusBadge tone="success">Default {workflow.default_request_kind?.replace(/_/g, ' ')}</StatusBadge> : null}
                      <StatusBadge tone={workflow.is_active ? 'info' : 'neutral'}>{workflow.is_active ? 'Active' : 'Inactive'}</StatusBadge>
                    </div>
                    <p className="max-w-3xl text-sm text-[hsl(var(--muted-foreground))]">{workflow.description || 'No description provided.'}</p>
                  </div>
                  <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/approval-workflows/${workflow.id}`)}>
                    Open builder
                  </button>
                </div>

                <div className="mt-5 grid gap-3 xl:grid-cols-4">
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Rules</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{workflow.rules.length}</p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Stages</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{workflow.stages.length}</p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Request coverage</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">
                      {workflow.rules.map((rule) => rule.request_kind).filter((value, index, list) => list.indexOf(value) === index).join(' • ') || 'None'}
                    </p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(workflow.modified_at)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}

      {!isCtMode && activeTab === 'inbox' ? (
        <SectionCard title="Approval inbox" description="Action pending requests here without mixing them into the workflow design surface.">
          <div className="space-y-3">
            {(inbox ?? []).map((action) => (
              <div key={action.id} className="surface-muted flex flex-col gap-3 rounded-[22px] px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="font-semibold text-[hsl(var(--foreground-strong))]">{action.subject_label}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    {action.requester_name} • {action.stage_name} • Owner: {action.owner_name}
                  </p>
                  {action.original_approver_name ? (
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      Routed via {action.assignment_source.toLowerCase()} from {action.original_approver_name}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge tone={getApprovalActionTone(action.status)}>{action.status}</StatusBadge>
                  {action.is_overdue ? <StatusBadge tone="danger">Overdue</StatusBadge> : null}
                  {action.assignment_source === 'ESCALATED' ? <StatusBadge tone="warning">Escalated</StatusBadge> : null}
                  {action.assignment_source === 'DELEGATED' ? <StatusBadge tone="info">Delegated</StatusBadge> : null}
                  <ApprovalDecisionDialog
                    actionLabel={`Approve ${action.subject_label}`}
                    triggerClassName="btn-secondary"
                    triggerLabel="Approve"
                    title="Approve request"
                    description="Add an optional note for the requester or the audit trail before approving this request."
                    confirmLabel="Approve request"
                    submitErrorFallback="Unable to approve this request."
                    isPending={approveMutation.isPending}
                    onSubmit={(comment) => approveMutation.mutateAsync({ actionId: action.id, comment })}
                  />
                  <ApprovalDecisionDialog
                    actionLabel={`Reject ${action.subject_label}`}
                    triggerClassName="btn-danger"
                    triggerLabel="Reject"
                    title="Reject request"
                    description="Rejection notes are required so requesters understand what must change."
                    confirmLabel="Reject request"
                    confirmTone="danger"
                    isCommentRequired
                    submitErrorFallback="Unable to reject this request."
                    isPending={rejectMutation.isPending}
                    onSubmit={(comment) => rejectMutation.mutateAsync({ actionId: action.id, comment })}
                  />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}

      {activeTab === 'settings' ? (
        <SectionCard title="Workflow health" description="Use these signals to spot gaps in approval configuration before they become operational issues.">
          <div className="grid gap-4 xl:grid-cols-4">
            <div className="surface-muted rounded-[20px] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Active workflows</p>
              <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{health.active}</p>
            </div>
            <div className="surface-muted rounded-[20px] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Default workflows</p>
              <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{health.defaults}</p>
            </div>
            <div className="surface-muted rounded-[20px] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Routing rules</p>
              <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{health.rules}</p>
            </div>
            <div className="surface-muted rounded-[20px] px-4 py-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">
                {isCtMode ? 'Workflow stages' : 'Pending approvals'}
              </p>
              <p className="mt-2 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">
                {isCtMode ? health.stages : inbox?.length ?? 0}
              </p>
            </div>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="surface-shell rounded-[20px] px-5 py-4">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">Recommended baseline</p>
              <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                Keep active defaults for leave, on-duty, attendance regularization, payroll processing, salary revision, and compensation template changes.
              </p>
            </div>
            <div className="surface-shell rounded-[20px] px-5 py-4">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">Current posture</p>
              <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                {health.defaults >= 5
                  ? 'Default coverage looks healthy. Review targeted rules and stage count next.'
                  : 'Review default workflow coverage. Leave, on-duty, attendance regularization, payroll processing, salary revision, and template change each need an active default.'}
              </p>
            </div>
          </div>
          {!isCtMode ? (
            <div className="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
              <form onSubmit={saveDelegation} className="surface-shell rounded-[20px] px-5 py-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Approval delegation</p>
                <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                  Redirect selected request kinds to another employee for a bounded date range.
                </p>
                <div className="mt-4 grid gap-4">
                  <div>
                    <label className="field-label">Delegator</label>
                    <AppSelect
                      value={delegationForm.delegator_employee_id}
                      onValueChange={(value) => setDelegationForm((current) => ({ ...current, delegator_employee_id: value }))}
                      options={employeeOptions}
                    />
                  </div>
                  <div>
                    <label className="field-label">Delegate</label>
                    <AppSelect
                      value={delegationForm.delegate_employee_id}
                      onValueChange={(value) => setDelegationForm((current) => ({ ...current, delegate_employee_id: value }))}
                      options={employeeOptions}
                    />
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="field-label">Start date</label>
                      <input
                        className="field-input"
                        type="date"
                        value={delegationForm.start_date}
                        onChange={(event) => setDelegationForm((current) => ({ ...current, start_date: event.target.value }))}
                      />
                    </div>
                    <div>
                      <label className="field-label">End date</label>
                      <input
                        className="field-input"
                        type="date"
                        value={delegationForm.end_date}
                        onChange={(event) => setDelegationForm((current) => ({ ...current, end_date: event.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    {APPROVAL_REQUEST_KIND_OPTIONS.map((requestKind) => (
                      <AppCheckbox
                        key={requestKind}
                        checked={delegationForm.request_kinds.includes(requestKind)}
                        onCheckedChange={(checked) =>
                          setDelegationForm((current) => ({
                            ...current,
                            request_kinds: checked
                              ? [...current.request_kinds, requestKind]
                              : current.request_kinds.filter((value) => value !== requestKind),
                          }))
                        }
                        label={requestKind.replace(/_/g, ' ')}
                      />
                    ))}
                  </div>
                  <AppCheckbox
                    checked={delegationForm.is_active}
                    onCheckedChange={(checked) => setDelegationForm((current) => ({ ...current, is_active: checked }))}
                    label="Delegation active"
                  />
                  <button type="submit" className="btn-primary" disabled={createDelegationMutation.isPending}>
                    Save delegation
                  </button>
                </div>
              </form>

              <div className="surface-shell rounded-[20px] px-5 py-5">
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">Current delegations</p>
                <div className="mt-4 space-y-3">
                  {approvalDelegations.length ? approvalDelegations.map((delegation) => (
                    <div key={delegation.id} className="surface-muted rounded-[18px] px-4 py-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-semibold text-[hsl(var(--foreground-strong))]">
                            {delegation.delegator_employee_name} → {delegation.delegate_employee_name}
                          </p>
                          <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                            {delegation.request_kinds.join(' • ')} • {delegation.start_date} to {delegation.end_date || 'Open ended'}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <StatusBadge tone={delegation.is_active ? 'success' : 'neutral'}>
                            {delegation.is_active ? 'Active' : 'Inactive'}
                          </StatusBadge>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() =>
                              void toggleDelegation(delegation.id, !delegation.is_active, {
                                delegator_employee: delegation.delegator_employee,
                                delegate_employee: delegation.delegate_employee,
                                request_kinds: delegation.request_kinds,
                                start_date: delegation.start_date,
                                end_date: delegation.end_date,
                              })
                            }
                          >
                            {delegation.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )) : (
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">No approval delegations configured yet.</p>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </SectionCard>
      ) : null}
    </div>
  )
}
