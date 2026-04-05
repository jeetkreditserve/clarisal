import { useNavigate, useParams } from 'react-router-dom'

import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useOnDutyPolicies, useOrgOnDutyRequests } from '@/hooks/useOrgAdmin'
import { useCtOrgConfiguration } from '@/hooks/useCtOrganisations'
import { formatDateTime } from '@/lib/format'

export function OnDutyPoliciesPage() {
  const navigate = useNavigate()
  const { organisationId } = useParams()
  const isCtMode = Boolean(organisationId)
  const basePath = isCtMode ? `/ct/organisations/${organisationId}` : '/org'
  const { data: policies, isLoading } = useOnDutyPolicies(!isCtMode)
  const { data: requests } = useOrgOnDutyRequests(!isCtMode)
  const { data: configuration, isLoading: isCtLoading } = useCtOrgConfiguration(organisationId ?? '', isCtMode)
  const resolvedPolicies = isCtMode ? configuration?.on_duty_policies : policies
  const pageLoading = isCtMode ? isCtLoading : isLoading

  if (pageLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  const activePolicies = resolvedPolicies?.filter((policy) => policy.is_active) ?? []
  const defaultPolicy = resolvedPolicies?.find((policy) => policy.is_default) ?? null

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={isCtMode ? 'Control Tower • OD configuration' : 'OD configuration'}
        title="On-duty policies"
        description="Govern travel, field work, and time-range OD submissions with richer rules than the old lightweight modal could express."
        actions={
          <>
            {isCtMode ? (
              <button type="button" className="btn-secondary" onClick={() => navigate(basePath)}>
                Back to organisation
              </button>
            ) : null}
            <button type="button" className="btn-primary" onClick={() => navigate(`${basePath}/on-duty-policies/new`)}>
              Build new policy
            </button>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-4">
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Configured policies</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{resolvedPolicies?.length ?? 0}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Active policies</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{activePolicies.length}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Default policy</p>
          <p className="mt-3 text-lg font-semibold text-[hsl(var(--foreground-strong))]">{defaultPolicy?.name ?? 'Not configured'}</p>
        </div>
        <div className="surface-card rounded-[28px] p-5">
          <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">OD requests tracked</p>
          <p className="mt-3 text-3xl font-semibold text-[hsl(var(--foreground-strong))]">{isCtMode ? '--' : requests?.length ?? 0}</p>
        </div>
      </div>

      <SectionCard title="Policy catalogue" description="Use full-page builders for OD policy editing so operational rules stay readable and extensible.">
        <div className="space-y-4">
          {(resolvedPolicies ?? []).map((policy) => {
            const policyRequestCount = isCtMode ? null : (requests ?? []).filter((request) => request.policy === policy.id).length
            return (
              <div key={policy.id} className="surface-muted rounded-[24px] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-lg font-semibold text-[hsl(var(--foreground-strong))]">{policy.name}</p>
                      {policy.is_default ? <StatusBadge tone="success">Default</StatusBadge> : null}
                      <StatusBadge tone={policy.is_active ? 'info' : 'neutral'}>{policy.is_active ? 'Active' : 'Inactive'}</StatusBadge>
                    </div>
                    <p className="max-w-3xl text-sm text-[hsl(var(--muted-foreground))]">{policy.description || 'No description provided for this policy.'}</p>
                  </div>
                  <button type="button" className="btn-secondary" onClick={() => navigate(`${basePath}/on-duty-policies/${policy.id}`)}>
                    Open builder
                  </button>
                </div>

                <div className="mt-5 grid gap-3 xl:grid-cols-4">
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Request modes</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">
                      {[policy.allow_half_day && 'Half day', policy.allow_time_range && 'Time range'].filter(Boolean).join(' • ') || 'Full day only'}
                    </p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Minimum notice</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{policy.min_notice_days} day(s)</p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Requests using policy</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{policyRequestCount ?? '--'}</p>
                  </div>
                  <div className="surface-shell rounded-[18px] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-[hsl(var(--muted-foreground))]">Last modified</p>
                    <p className="mt-2 font-medium text-[hsl(var(--foreground-strong))]">{formatDateTime(policy.modified_at)}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>
    </div>
  )
}
