import { useMemo } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { ApprovalDecisionDialog } from '@/components/ui/ApprovalDecisionDialog'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useApprovalInbox,
  useApprovalWorkflows,
  useApproveApprovalAction,
  useRejectApprovalAction,
} from '@/hooks/useOrgAdmin'
import { useCtOrgConfiguration } from '@/hooks/useCtOrganisations'
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
  const { data: workflows, isLoading } = useApprovalWorkflows()
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const { data: inbox } = useApprovalInbox()
  const approveMutation = useApproveApprovalAction()
  const rejectMutation = useRejectApprovalAction()
  const resolvedWorkflows = isCtMode ? configuration?.approval_workflows : workflows
  const pageLoading = isCtMode ? isCtLoading : isLoading

  const health = useMemo(() => {
    const workflowList = resolvedWorkflows ?? []
    return {
      active: workflowList.filter((workflow) => workflow.is_active).length,
      defaults: workflowList.filter((workflow) => workflow.is_default).length,
      rules: workflowList.reduce((sum, workflow) => sum + workflow.rules.length, 0),
      stages: workflowList.reduce((sum, workflow) => sum + workflow.stages.length, 0),
    }
  }, [resolvedWorkflows])

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
                    {action.requester_name} • {action.stage_name}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge tone={getApprovalActionTone(action.status)}>{action.status}</StatusBadge>
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
                Keep one default each for leave, on-duty, and attendance regularization, and avoid stage definitions without fallback handling.
              </p>
            </div>
            <div className="surface-shell rounded-[20px] px-5 py-4">
              <p className="font-semibold text-[hsl(var(--foreground-strong))]">Current posture</p>
              <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                {health.defaults >= 3
                  ? 'Default coverage looks healthy. Review targeted rules and stage count next.'
                  : 'Review default workflow coverage. Leave, on-duty, and attendance regularization each need an active default.'}
              </p>
            </div>
          </div>
        </SectionCard>
      ) : null}
    </div>
  )
}
