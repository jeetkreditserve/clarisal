import { useNavigate, useParams } from 'react-router-dom'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useLeavePlans } from '@/hooks/useOrgAdmin'
import { useCtOrgConfiguration } from '@/hooks/useCtOrganisations'
import { formatDateTime } from '@/lib/format'

export function LeavePlansPage() {
  const navigate = useNavigate()
  const { organisationId } = useParams()
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const { data: plans, isLoading } = useLeavePlans()
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const resolvedPlans = isCtMode ? configuration?.leave_plans : plans
  const pageLoading = isCtMode ? isCtLoading : isLoading

  if (pageLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const activePlans = resolvedPlans?.filter((plan) => plan.is_active) ?? []
  const defaultPlan = resolvedPlans?.find((plan) => plan.is_default) ?? null
  const totalLeaveTypes = (resolvedPlans ?? []).reduce((sum, plan) => sum + plan.leave_types.length, 0)

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • Leave configuration' : 'Leave configuration'}
        title="Leave plans"
        description="Design full leave policies with multiple leave types, entitlement logic, and targeted applicability rules."
        actions={
          <>
            {isCtMode ? (
              <button type="button" className="btn-secondary" onClick={() => navigate(basePath)}>
                Back to organisation
              </button>
            ) : null}
            <button type="button" className="btn-primary" onClick={() => navigate(`${basePath}/leave-plans/new`)}>
              Build new plan
            </button>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-4">
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Configured plans</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{resolvedPlans?.length ?? 0}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Active plans</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{activePlans.length}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Default plan</p>
          <p className="mt-3 text-lg font-semibold text-[hsl(var(--foreground-strong))]">{defaultPlan?.name ?? 'Not configured'}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Leave types across plans</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{totalLeaveTypes}</p>
        </div>
      </div>

      <SectionCard
        title="Policy catalogue"
        description="Open a dedicated builder to maintain leave types, accrual rules, carry-forward behavior, and applicability filters."
      >
        <div className="space-y-4">
          {(resolvedPlans ?? []).map((plan) => (
            <div key={plan.id} className="surface-muted rounded-[24px] p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{plan.name}</p>
                    {plan.is_default ? <StatusBadge tone="success">Default</StatusBadge> : null}
                    <StatusBadge tone={plan.is_active ? 'info' : 'neutral'}>{plan.is_active ? 'Active' : 'Inactive'}</StatusBadge>
                  </div>
                  <p className="max-w-3xl text-sm text-[hsl(var(--muted-foreground))]">{plan.description || 'No description provided for this policy.'}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/leave-plans/${plan.id}`)}>
                    Open builder
                  </button>
                </div>
              </div>

              <div className="mt-5 grid gap-3 xl:grid-cols-4">
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Cycle</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{plan.leave_cycle.name}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Leave types</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{plan.leave_types.length}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Applicability rules</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{plan.rules.length}</p>
                </div>
                <div className="surface-shell rounded-[18px] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
                  <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(plan.modified_at)}</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 xl:grid-cols-2">
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Leave types in this plan</p>
                  <div className="flex flex-wrap gap-2">
                    {plan.leave_types.map((leaveType) => (
                      <span
                        key={leaveType.id}
                        className="rounded-full border border-[hsl(var(--border)_/_0.7)] px-3 py-1 text-xs font-medium text-[hsl(var(--foreground-strong))]"
                      >
                        {leaveType.name} • {leaveType.annual_entitlement} days
                      </span>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Rule coverage</p>
                  <div className="flex flex-wrap gap-2">
                    {plan.rules.length === 0 ? (
                      <span className="rounded-full border border-dashed border-[hsl(var(--border)_/_0.7)] px-3 py-1 text-xs text-[hsl(var(--muted-foreground))]">
                        No targeted rules
                      </span>
                    ) : (
                      plan.rules.map((rule) => (
                        <span
                          key={rule.id}
                          className="rounded-full border border-[hsl(var(--border)_/_0.7)] px-3 py-1 text-xs font-medium text-[hsl(var(--foreground-strong))]"
                        >
                          {rule.name}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}
