import { useState } from 'react'
import { toast } from 'sonner'

import { FieldErrorText } from '@/components/ui/FieldErrorText'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { useCreateOnDutyPolicy, useOnDutyPolicies } from '@/hooks/useOrgAdmin'
import { createDefaultOnDutyPolicyForm } from '@/lib/constants'
import { getErrorMessage, getFieldErrors } from '@/lib/errors'

export function OnDutyPoliciesPage() {
  const { data: policies, isLoading } = useOnDutyPolicies()
  const createPolicyMutation = useCreateOnDutyPolicy()
  const [policyForm, setPolicyForm] = useState(createDefaultOnDutyPolicyForm)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const handlePolicySubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setFieldErrors({})
    try {
      await createPolicyMutation.mutateAsync(policyForm)
      toast.success('On-duty policy created.')
      setPolicyForm(createDefaultOnDutyPolicyForm())
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error)
      setFieldErrors(nextFieldErrors)
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.error(getErrorMessage(error, 'Unable to create on-duty policy.'))
      }
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
        eyebrow="OD configuration"
        title="On-duty policies"
        description="Separate OD policy rules from leave plans so travel, field work, and time-range requests stay easy to govern."
      />

      <div className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
        <SectionCard title="Create OD policy" description="Define whether employees can request full-day, half-day, or time-range on-duty approvals.">
          <form onSubmit={handlePolicySubmit} className="grid gap-4">
            <div>
              <label className="field-label" htmlFor="od-policy-name">
                Policy name
              </label>
              <input
                id="od-policy-name"
                className="field-input"
                value={policyForm.name}
                onChange={(event) => setPolicyForm((current) => ({ ...current, name: event.target.value }))}
                required
              />
              <FieldErrorText message={fieldErrors.name} />
            </div>
            <div>
              <label className="field-label" htmlFor="od-policy-description">
                Description
              </label>
              <textarea
                id="od-policy-description"
                className="field-textarea"
                value={policyForm.description}
                onChange={(event) => setPolicyForm((current) => ({ ...current, description: event.target.value }))}
              />
            </div>
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                type="checkbox"
                checked={policyForm.allow_time_range}
                onChange={(event) => setPolicyForm((current) => ({ ...current, allow_time_range: event.target.checked }))}
              />
              Allow time-range requests
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                type="checkbox"
                checked={policyForm.allow_half_day}
                onChange={(event) => setPolicyForm((current) => ({ ...current, allow_half_day: event.target.checked }))}
              />
              Allow half-day OD
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
              <input
                type="checkbox"
                checked={policyForm.requires_attachment}
                onChange={(event) => setPolicyForm((current) => ({ ...current, requires_attachment: event.target.checked }))}
              />
              Require attachment on submission
            </label>
            <button type="submit" className="btn-primary" disabled={createPolicyMutation.isPending}>
              Save OD policy
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Configured OD policies" description="Keep policy rules readable so field-work and travel approvals are easy to maintain.">
          <div className="space-y-3">
            {policies?.map((policy) => (
              <div key={policy.id} className="surface-muted rounded-[20px] px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{policy.name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{policy.description || 'No description set'}</p>
                  </div>
                  <div className="text-sm text-[hsl(var(--muted-foreground))]">{policy.is_default ? 'Default policy' : 'Secondary policy'}</div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}
